# Dokumentasi Teknis: Modul Data & Indicators Engineer
**Proyek:** Stock Trading Expert System (BEI/IDX)  
**Metode:** Rule-Based Expert System (Forward Chaining & Fuzzy Logic)

---

## 1. Gambaran Umum & Tanggung Jawab Modul
Modul **Data & Indicators Engineer** adalah fondasi utama yang menyiapkan fakta awal (*initial facts*) bagi sistem pakar sebelum diproses oleh *Inference Engine*. Tugas utama modul ini meliputi:
1. **Akuisisi Data Otomatis (Yahoo Finance Scraper):** Mengambil data harga harian saham BEI/IDX (kode `.JK`) dengan pembaruan otomatis setiap **15 menit** pada jam perdagangan bursa (status data *Sementara*) dan finalisasi pada pukul **16:30 WIB** (status data *Final EOD*).
2. **Penyimpanan Bertahap (*Incremental Storage*) & Pra-pemrosesan:** Menyimpan data historis 3 tahun ke lokal, hanya mengunduh baris data terbaru pada pembaruan berikutnya, mengurutkan tanggal secara kronologis, membuang hari libur bursa (`Volume == 0`), dan menangani nilai kosong (*missing values*).
3. **Perhitungan Indikator & Fakta Turunan:** Menghitung indikator teknikal utama serta menurunkannya menjadi variabel input Fuzzy, filter validasi sinyal (tren & *N-Period Min-Max* / NPMM), serta manajemen risiko berbasis volatilitas.
4. **Ekspor File Siap Pakai (*File-Based Output*):** Menghasilkan file `.csv` (untuk *Backtesting* & *Dashboard Grafik*) dan file `.json` (untuk *Inference Engine* harian) sehingga modul lain dapat langsung membaca hasil indikator dari file.

---

## 2. Logika Indikator & Transformasi ke Sistem Pakar Fuzzy

Dalam analisis teknikal visual, trader biasanya mengamati persilangan garis (*line crossing*) atau sentuhan *candlestick* pada pita indikator. Namun, di dalam sistem pakar berbasis **Logika Fuzzy**, kondisi visual yang biner (*ya/tidak*) diubah menjadi **nilai kontinu (angka terukur)** agar derajat keanggotaannya dapat dihitung secara matematis:

### A. Dari *MACD Crossing* menjadi Histogram MACD (`MACD_Hist`)
* **Konsep Visual Trader:** Sinyal beli muncul saat *MACD Line* memotong ke atas *Signal Line* (*Golden Cross*), dan melemah saat memotong ke bawah (*Death Cross*).
* **Implementasi Sistem Pakar:** Sistem menghitung selisih kedua garis tersebut:
  $$\text{MACD\_Hist} = \text{MACD\_Line} - \text{MACD\_Signal}$$
  * Saat tepat bersilangan (*crossing*), nilai $\text{MACD\_Hist} = 0$.
  * Setelah *Golden Cross* (momentum naik), $\text{MACD\_Hist} > 0$ (**Positif**). Semakin besar nilainya, semakin kuat momentum kenaikannya (digunakan pada aturan **R1** dan **R3**).
  * Setelah *Death Cross* (momentum turun), $\text{MACD\_Hist} < 0$ (**Negatif**), yang memicu pelemahan sinyal beli pada aturan **R4**.

### B. Dari *Bollinger Candle Touch* menjadi Persen B (`BB_PctB` / $\%B$)
* **Konsep Visual Trader:** Peluang beli saat harga terkoreksi (*buy on weakness*) dilihat ketika *candle* menyentuh atau sedikit menembus pita bawah (*Lower Band*).
* **Implementasi Sistem Pakar:** Karena tiap saham memiliki nominal harga berbeda, posisi harga dinormalisasi terhadap lebar pita Bollinger menggunakan rumus $\%B$:
  $$\%B = \frac{\text{Close} - \text{BB\_Lower}}{\text{BB\_Upper} - \text{BB\_Lower}}$$
  * $\%B \le 0$: Harga menyentuh atau menembus *Lower Band*.
  * $\%B \approx 0.1 - 0.2$ (**Rendah**): Harga berada dekat di atas *Lower Band* (digunakan pada aturan **R2**).
  * $\%B = 0.5$: Harga berada tepat di garis tengah ($\text{SMA}_{20}$).
  * $\%B \ge 1.0$: Harga menyentuh atau menembus *Upper Band*.

### C. Makna Rekomendasi `BELI` vs `TAHAN` serta Mekanisme *Exit* (TP/SL)
* **Arti Keputusan `TAHAN`:** Di dalam sistem ini, `TAHAN` berarti **"Tahan diri untuk tidak membeli dulu"** (*Wait and See* / *No Entry*), bukan menahan saham yang sudah dibeli. Hal ini terjadi jika filter validasi gagal (`Signal_Valid == False`) atau skor kekuatan sinyal beli dari defuzzifikasi bernilai $< 70$.
* **Arti Keputusan `BELI`:** Dihasilkan apabila `Signal_Valid == True` dan skor kekuatan sinyal beli mencapai $\ge 70$.
* **Kapan Harus Menjual (*Exit Position*)?** Penjualan tidak menunggu perubahan sinyal harian, melainkan diatur otomatis menggunakan manajemen risiko berbasis volatilitas $\text{ATR}(14)$ yang dikunci saat sinyal `BELI` muncul:
  * **Take Profit (TP):** $\text{Harga Masuk} + (3 \times \text{ATR}_{14})$
  * **Stop Loss (SL):** $\text{Harga Masuk} - (1.5 \times \text{ATR}_{14})$

---

## 3. Daftar Variabel yang Dihasilkan Modul

| Kategori | Nama Kolom / Key | Rumus / Logika Perhitungan | Kegunaan pada Tahap Selanjutnya |
| :--- | :--- | :--- | :--- |
| **Input Fuzzy 1** | `RSI_14` / `rsi_14` | Wilder's Smoothing RSI 14 hari ($0 - 100$) | Deteksi jenuh jual ($<30$) atau jenuh beli ($>70$) pada R1, R2, R4 |
| **Input Fuzzy 2** | `MACD_Hist` / `macd_hist` | $\text{EMA}_{12} - \text{EMA}_{26} - \text{Signal}_9$ | Deteksi momentum naik (positif) atau turun (negatif) pada R1, R3, R4 |
| **Input Fuzzy 3** | `BB_PctB` / `bb_pct_b` | $\frac{\text{Close} - \text{BB\_Lower}}{\text{BB\_Upper} - \text{BB\_Lower}}$ | Mengukur posisi harga dalam Bollinger Bands $(20, 2)$ pada R2 |
| **Input Fuzzy 4** | `Volume_Ratio` / `volume_ratio` | $\frac{\text{Volume}}{\text{SMA}(\text{Volume}, 20)}$ | Mengukur lonjakan volume terhadap rata-rata 20 hari pada R3 |
| **Filter Tren** | `Is_Uptrend` / `is_uptrend` | $\text{SMA}_{20} > \text{SMA}_{50}$ | Syarat pertama validasi sinyal (konfirmasi tren naik) |
| **Filter NPMM** | `Near_Local_Min` / `near_local_min` | $\frac{\text{Close} - \min(\text{Low}_N)}{\min(\text{Low}_N)} \le 0.03$ | Syarat kedua validasi sinyal (harga $\le 3\%$ dari titik terendah $N$ hari terakhir tanpa *look-ahead bias*) |
| **Fakta Tahap 3** | `Signal_Valid` / `signal_valid` | `Is_Uptrend` $\land$ `Near_Local_Min` | Penentu apakah aturan Fuzzy R1–R4 dievaluasi atau langsung `TAHAN` |
| **Risiko (ATR)** | `ATR_14` / `atr_14` | Wilder's Smoothing *True Range* 14 hari | Dasar perhitungan jarak harga *Take Profit* ($3\times$) dan *Stop Loss* ($1.5\times$) |

---

## 4. Struktur Direktori & File Output

Saat program dijalankan, sistem secara otomatis membuat struktur folder berikut agar modul *Inference Engine*, *Backtesting*, dan *Dashboard Web* dapat langsung membaca data dari file:

```text
storage_data/
├── 1_raw_incremental/                  # Penyimpanan bertahap data mentah (OHLCV)
│   ├── BBCA_raw_daily.csv
│   ├── BBRI_raw_daily.csv
│   └── TLKM_raw_daily.csv
│
└── 2_inference_ready/                  # File bersih siap pakai untuk modul selanjutnya
    ├── BBCA_clean_indicators.csv       # DataFrame 3 tahun + indikator (Untuk Backtesting & Grafik)
    ├── BBCA_latest_facts.json          # Fakta indikator hari terakhir BBCA (Untuk Inference Engine)
    ├── BBRI_clean_indicators.csv
    ├── BBRI_latest_facts.json
    ├── TLKM_clean_indicators.csv
    ├── TLKM_latest_facts.json
    └── ALL_STOCKS_latest_facts.json    # Gabungan fakta hari terakhir seluruh saham
```

---

## 5. Kode Sumber Lengkap (`data_indicators_engineer.py`)

### Instalasi Dependensi
```bash
pip install yfinance pandas numpy schedule pytz
```

### Implementasi Kode Python
```python
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

        # Bulatkan angka desimal agar file CSV bersih dan rapi
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
        code = self.clean_code(ticker)
        raw_df = self.fetch_and_store(ticker)
        clean_df = self.calculate_indicators(raw_df)

        if clean_df.empty:
            raise ValueError(f"Data tidak cukup untuk menghitung indikator pada saham {ticker}")

        # 1. Simpan Clean DataFrame + Indikator ke File CSV
        clean_csv_path = os.path.join(self.out_dir, f"{code}_clean_indicators.csv")
        clean_df.to_csv(clean_csv_path)

        # 2. Susun Fakta Hari Terakhir dan Simpan ke File JSON
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

    summary_json_path = os.path.join(engineer.out_dir, "ALL_STOCKS_latest_facts.json")
    with open(summary_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_latest_facts, f, indent=4)
    print(f" [OK] Ringkasan Semua Saham -> {summary_json_path}")


if __name__ == "__main__":
    engineer = StockDataIndicatorEngineer(base_dir="storage_data")
    daftar_saham = ["BBCA", "BBRI", "TLKM"]

    print("Mengekspor file indikator awal...")
    update_all_stocks(engineer, daftar_saham, is_final=True)

    schedule.every(15).minutes.do(update_all_stocks, engineer=engineer, tickers=daftar_saham, is_final=False)
    schedule.every().day.at("16:30", "Asia/Jakarta").do(update_all_stocks, engineer=engineer, tickers=daftar_saham, is_final=True)

    print("\nScheduler berjalan. File di folder 'storage_data/2_inference_ready' akan selalu ter-update otomatis.")
    while True:
        schedule.run_pending()
        time.sleep(1)
```

---

## 6. Panduan Integrasi untuk Modul Selanjutnya (*Inference Engine* & *Backtesting*)

Anggota tim yang mengerjakan *Inference Engine* atau *Dashboard* tidak perlu memanggil ulang fungsi *scraper*, melainkan cukup membaca file yang sudah tersedia di folder `storage_data/2_inference_ready/`:

### A. Membaca Fakta Harian dari File JSON (Untuk *Inference Engine*)
```python
import json

with open("storage_data/2_inference_ready/BBCA_latest_facts.json", "r") as f:
    facts = json.load(f)

# 1. Cek validasi sinyal Tahap 3 (Tren & NPMM)
if not facts["validation_filter"]["signal_valid"]:
    keputusan = "TAHAN (Sinyal Tidak Valid)"
else:
    # 2. Ambil 4 input untuk Fuzzifikasi
    rsi = facts["fuzzy_inputs"]["rsi_14"]
    macd_hist = facts["fuzzy_inputs"]["macd_hist"]
    bb_pct_b = facts["fuzzy_inputs"]["bb_pct_b"]
    vol_ratio = facts["fuzzy_inputs"]["volume_ratio"]
    # Lanjutkan ke perhitungan derajat keanggotaan & aturan R1-R4...
```

### B. Membaca Data Historis 3 Tahun dari File CSV (Untuk *Backtesting* & *Visualisasi*)
```python
import pandas as pd

df = pd.read_csv(
    "storage_data/2_inference_ready/BBCA_clean_indicators.csv", 
    index_col="Date", 
    parse_dates=True
)

# Seluruh kolom indikator sudah tersedia dan bersih dari nilai NaN
print(df[["Close", "RSI_14", "MACD_Hist", "BB_PctB", "Volume_Ratio", "Signal_Valid", "ATR_14"]].tail())
```