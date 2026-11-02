import os
import json
import time
from datetime import datetime
import pytz
import schedule
import yfinance as yf
import pandas as pd
import numpy as np

class StockDataIndicatorEngineer:
    def __init__(self, base_dir="storage_data"):
        self.tz = pytz.timezone('Asia/Jakarta')
        
        # Pisahkan folder data mentah dan folder output siap pakai untuk Inference Engine
        self.raw_dir = os.path.join(base_dir, "1_raw_incremental")
        self.out_dir = os.path.join(base_dir, "2_inference_ready")
        
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)

    def format_ticker(self, ticker: str) -> str:
        """Memastikan kode saham menggunakan akhiran .JK untuk BEI/IDX."""
        ticker = ticker.upper().strip()
        return ticker if ticker.endswith(".JK") else f"{ticker}.JK"

    def clean_code(self, ticker: str) -> str:
        """Mengambil kode saham tanpa .JK untuk penamaan file (misal: BBCA)."""
        return ticker.upper().strip().replace(".JK", "")

    # ==========================================
    # 1. SCRAPER & INCREMENTAL STORAGE
    # ==========================================
    def fetch_and_store(self, ticker: str, period_years: int = 3) -> pd.DataFrame:
        """Mengambil data dari Yahoo Finance dan menyimpannya secara incremental."""
        jk_ticker = self.format_ticker(ticker)
        code = self.clean_code(ticker)
        raw_file_path = os.path.join(self.raw_dir, f"{code}_raw_daily.csv")

        if os.path.exists(raw_file_path):
            existing_df = pd.read_csv(raw_file_path, index_col='Date', parse_dates=True)
            last_date = existing_df.index.max()
            
            new_df = yf.download(jk_ticker, start=last_date.strftime('%Y-%m-%d'), progress=False)
            if not new_df.empty:
                new_df = self._clean_yfinance_df(new_df)
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            else:
                combined_df = existing_df
        else:
            raw_df = yf.download(jk_ticker, period=f"{period_years}y", progress=False)
            combined_df = self._clean_yfinance_df(raw_df)

        combined_df = self.preprocess_data(combined_df)
        combined_df.to_csv(raw_file_path)
        return combined_df

    def _clean_yfinance_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index.name = 'Date'
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        return df[[c for c in cols if c in df.columns]].copy()

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.sort_index(ascending=True)
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'], how='all')
        df = df[df['Volume'] > 0]
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].ffill()
        df['Volume'] = df['Volume'].fillna(0)
        return df

    # ==========================================
    # 2. PERHITUNGAN INDIKATOR TEKNIKAL
    # ==========================================
    def calculate_indicators(self, df: pd.DataFrame, npmm_window: int = 5, local_min_tol: float = 0.03) -> pd.DataFrame:
        data = df.copy()

        # 1. Moving Average: SMA 20 & SMA 50
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()

        # 2. Volume & Rasio Volume (Input Fuzzy)
        data['Volume_SMA_20'] = data['Volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA_20']

        # 3. RSI (14) - Wilder's Smoothing (Input Fuzzy)
        delta = data['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        data['RSI_14'] = 100 - (100 / (1 + rs))
        data['RSI_14'] = data['RSI_14'].fillna(100)

        # 4. MACD (12, 26, 9) & Histogram (Input Fuzzy)
        ema_12 = data['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD_Line'] = ema_12 - ema_26
        data['MACD_Signal'] = data['MACD_Line'].ewm(span=9, adjust=False).mean()
        data['MACD_Hist'] = data['MACD_Line'] - data['MACD_Signal']

        # 5. Bollinger Bands (20, 2) & %B (Input Fuzzy)
        bb_std = data['Close'].rolling(window=20).std()
        data['BB_Middle'] = data['SMA_20']
        data['BB_Upper'] = data['BB_Middle'] + (2 * bb_std)
        data['BB_Lower'] = data['BB_Middle'] - (2 * bb_std)
        bb_range = (data['BB_Upper'] - data['BB_Lower']).replace(0, np.nan)
        data['BB_PctB'] = (data['Close'] - data['BB_Lower']) / bb_range

        # 6. ATR (14) - Penentuan TP & SL
        high_low = data['High'] - data['Low']
        high_close = (data['High'] - data['Close'].shift(1)).abs()
        low_close = (data['Low'] - data['Close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['ATR_14'] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        # 7. Filter Validasi Sinyal (Tahap 3: Tren Naik & Dekat Minimum Lokal NPMM)
        data['Is_Uptrend'] = data['SMA_20'] > data['SMA_50']
        data['Local_Min_N'] = data['Low'].rolling(window=npmm_window).min()
        data['Near_Local_Min'] = (data['Close'] - data['Local_Min_N']) / data['Local_Min_N'] <= local_min_tol
        data['Signal_Valid'] = data['Is_Uptrend'] & data['Near_Local_Min']

        # Bulatkan angka desimal agar file CSV bersih dan rapi saat dibuka
        float_cols = ['SMA_20', 'SMA_50', 'Volume_SMA_20', 'Volume_Ratio', 'RSI_14', 
                      'MACD_Line', 'MACD_Signal', 'MACD_Hist', 'BB_Middle', 'BB_Upper', 
                      'BB_Lower', 'BB_PctB', 'ATR_14', 'Local_Min_N']
        data[float_cols] = data[float_cols].round(4)

        clean_df = data.dropna().copy()
        return clean_df

    # ==========================================
    # 3. EXPORT FILE SIAP PAKAI (CSV & JSON)
    # ==========================================
    def process_and_export_files(self, ticker: str, is_final: bool = False) -> dict:
        """
        Menghitung indikator lalu langsung menyimpannya ke dalam file CSV dan JSON
        agar bisa langsung dibaca oleh modul Inference Engine / anggota tim lain.
        """
        code = self.clean_code(ticker)
        raw_df = self.fetch_and_store(ticker)
        clean_df = self.calculate_indicators(raw_df)

        if clean_df.empty:
            raise ValueError(f"Data tidak cukup untuk menghitung indikator pada saham {ticker}")

        # 1. Simpan Clean DataFrame + Indikator ke File CSV (Untuk Backtesting & Grafik)
        clean_csv_path = os.path.join(self.out_dir, f"{code}_clean_indicators.csv")
        clean_df.to_csv(clean_csv_path)

        # 2. Susun Fakta Hari Terakhir dan Simpan ke File JSON (Untuk Inference Engine Harian)
        latest = clean_df.iloc[-1]
        latest_date = clean_df.index[-1].strftime('%Y-%m-%d')

        inference_facts = {
            "metadata": {
                "ticker": self.format_ticker(ticker),
                "code": code,
                "date": latest_date,
                "timestamp_update": datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S WIB'),
                "status_data": "FINAL (EOD)" if is_final else "SEMENTARA (Intraday Delayed ~15m)",
                "source_csv_file": clean_csv_path
            },
            "price_volume": {
                "open": float(latest['Open']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "close": float(latest['Close']),
                "volume": int(latest['Volume'])
            },
            "fuzzy_inputs": {
                "rsi_14": float(latest['RSI_14']),
                "macd_hist": float(latest['MACD_Hist']),
                "bb_pct_b": float(latest['BB_PctB']),
                "volume_ratio": float(latest['Volume_Ratio'])
            },
            "validation_filter": {
                "sma_20": float(latest['SMA_20']),
                "sma_50": float(latest['SMA_50']),
                "is_uptrend": bool(latest['Is_Uptrend']),
                "local_min_n": float(latest['Local_Min_N']),
                "near_local_min": bool(latest['Near_Local_Min']),
                "signal_valid": bool(latest['Signal_Valid'])
            },
            "risk_management": {
                "atr_14": float(latest['ATR_14']),
                "initial_sl_estimate": round(float(latest['Close'] - 1.5 * latest['ATR_14']), 2),
                "initial_tp_estimate": round(float(latest['Close'] + 3.0 * latest['ATR_14']), 2)
            }
        }

        facts_json_path = os.path.join(self.out_dir, f"{code}_latest_facts.json")
        with open(facts_json_path, 'w', encoding='utf-8') as f:
            json.dump(inference_facts, f, indent=4)

        return {
            "ticker": code,
            "csv_path": clean_csv_path,
            "json_path": facts_json_path,
            "facts": inference_facts
        }


# ==========================================
# 4. SCHEDULER OTOMATIS (15 MENIT & 16:30 WIB)
# ==========================================
def update_all_stocks(engineer: StockDataIndicatorEngineer, tickers: list, is_final: bool = False):
    now = datetime.now(engineer.tz)
    # Untuk intraday, hanya jalan Senin-Jumat jam 09:00 - 16:15 WIB
    if not is_final:
        if not (now.weekday() < 5 and (9 <= now.hour < 16 or (now.hour == 16 and now.minute <= 15))):
            return

    label = "FINAL EOD 16:30" if is_final else "INTRADAY 15m"
    print(f"\n[{now.strftime('%H:%M:%S WIB')}] === UPDATE FILE INDIKATOR ({label}) ===")
    
    all_latest_facts = {}
    for t in tickers:
        res = engineer.process_and_export_files(t, is_final=is_final)
        all_latest_facts[res["ticker"]] = res["facts"]
        print(f" [OK] {res['ticker']} -> CSV: {res['csv_path']} | JSON: {res['json_path']}")

    # Simpan juga 1 file gabungan JSON berisi seluruh saham agar Inference Engine bisa baca sekaligus
    summary_json_path = os.path.join(engineer.out_dir, "ALL_STOCKS_latest_facts.json")
    with open(summary_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_latest_facts, f, indent=4)
    print(f" [OK] Ringkasan Semua Saham -> {summary_json_path}")


if __name__ == "__main__":
    engineer = StockDataIndicatorEngineer(base_dir="storage_data")
    daftar_saham = ["BBCA", "BBRI", "TLKM"]

    # Eksekusi pertama kali saat script dijalankan agar file langsung terbentuk
    print("Mengekspor file indikator awal...")
    update_all_stocks(engineer, daftar_saham, is_final=True)

    # Jadwalkan auto-refresh tiap 15 menit & finalisasi 16:30 WIB
    schedule.every(15).minutes.do(update_all_stocks, engineer=engineer, tickers=daftar_saham, is_final=False)
    schedule.every().day.at("16:30", "Asia/Jakarta").do(update_all_stocks, engineer=engineer, tickers=daftar_saham, is_final=True)

    print("\nScheduler berjalan. File di folder 'storage_data/2_inference_ready' akan selalu ter-update otomatis.")
    while True:
        schedule.run_pending()
        time.sleep(1)