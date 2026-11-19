# Dokumentasi Teknis: Modul Data & Indicators Engineer
**Proyek:** Stock Trading Expert System (BEI/IDX)
**Metode:** Rule-Based Expert System — Forward Chaining + Event-Driven Indicator Crossing (tanpa fuzzy)

---

## 1. Gambaran Umum & Tanggung Jawab Modul

Modul **Data & Indicators Engineer** adalah fondasi yang menyiapkan fakta awal (*initial facts*) bagi *Inference Engine*. Tugas utamanya:

1. **Akuisisi Data Otomatis (Yahoo Finance):** Mengambil data harga harian saham BEI/IDX (kode `.JK`) dengan pembaruan intraday setiap **15 menit** pada jam bursa (status *Sementara*) dan finalisasi pukul **16:30 WIB** (status *Final EOD*).
2. **Penyimpanan Bertahap (*Incremental Storage*) & Pra-pemrosesan:** Menyimpan historis 3 tahun, hanya mengunduh baris baru, mengurutkan tanggal, membuang hari libur (`Volume == 0`), dan menangani nilai kosong.
3. **Perhitungan Indikator & Fakta Turunan:** Menghitung RSI 14, MACD Histogram, Bollinger %B, ATR 14, serta filter validasi sinyal (tren SMA dan kedekatan minimum lokal NPMM) **tanpa look-ahead bias**.
4. **Ekspor File Siap Pakai:** Menghasilkan `.csv` (backtesting & chart) dan `.json` (inference engine harian), termasuk nilai hari ini ($t$), kemarin ($t-1$), dan dua hari lalu ($t-2$) yang dibutuhkan untuk mendeteksi pemicu.

Modul ini **tidak** melakukan fuzzifikasi, fungsi keanggotaan, atau defuzzifikasi. Seluruh keputusan dihasilkan oleh basis aturan IF–THEN pada `src/rule_engine/`.

---

## 2. Logika Indikator & Transformasi ke Sistem Pakar Rule-Based

Sistem pakar ini bekerja dengan **kejadian diskret (crisp Boolean)**: garis indikator *disentuh* atau *dilewati*, dibandingkan antara hari ini ($t$) dan hari sebelumnya ($t-1$, serta $t-2$ untuk pola pantulan).

### A. MACD Histogram (`MACD_Hist`)
$$\text{MACD\_Hist} = \text{MACD\_Line} - \text{MACD\_Signal}$$

| Kejadian | Kondisi | Aturan |
| :--- | :--- | :--- |
| Merah → Hijau (tembus 0 ke atas) | $\text{Hist}_{t-1} \le 0 < \text{Hist}_t$ | **R2 — BELI** (dengan syarat RSI < 70) |
| Hijau → Merah (tembus 0 ke bawah) | $\text{Hist}_{t-1} \ge 0 > \text{Hist}_t$ | **R7 — TAHAN** |

### B. Bollinger %B (`BB_PctB`)
$$\%B = \frac{\text{Close} - \text{BB\_Lower}}{\text{BB\_Upper} - \text{BB\_Lower}}$$

Garis acuan: **0.0** (bawah), **0.5** (tengah/pivot), **1.0** (atas).

| Kejadian | Kondisi | Aturan |
| :--- | :--- | :--- |
| Menyentuh 0 dari atas | $\%B_{t-1} > 0$ dan $\%B_t \le 0$ | **R3 — BELI** |
| Menembus 0.5 ke atas | $\%B_{t-1} < 0.5 \le \%B_t < 1$ | **R4 — BELI** (RSI < 70) |
| Memantul naik di 0.5 | turun mendekati 0.5 lalu naik lagi | **R5 — BELI** (RSI < 70) |
| Menyentuh 1 dari bawah | $\%B_{t-1} < 1 \le \%B_t$ | **R8 — TAHAN** |
| Menembus 0.5 ke bawah | $\%B_{t-1} > 0.5 \ge \%B_t > 0$ | **R9 — TAHAN** |
| Ditolak di 0.5 | naik mendekati 0.5 lalu turun lagi | **R10 — TAHAN** |

### C. RSI 14 (`RSI_14`)
* **Menyentuh 30 dari atas:** $\text{RSI}_{t-1} > 30$ dan $\text{RSI}_t \le 30$ → **R1 — BELI**.
* **Menyentuh 70 dari bawah:** $\text{RSI}_{t-1} < 70$ dan $\text{RSI}_t \ge 70$ → **R6 — TAHAN**.
* **Zona momentum $30 < \text{RSI} < 70$:** bukan pemicu mandiri, melainkan syarat pendukung R2/R4/R5 (`below_70`).

### D. Makna `BELI` vs `TAHAN` serta Mekanisme Exit (TP/SL)
* **`TAHAN`** berarti **"tahan diri untuk tidak membeli dulu"** (*wait and see* / no entry). Terjadi jika:
  1. filter validasi Tahap 3 gagal (`Signal_Valid == False`), **atau**
  2. tidak ada aturan BELI yang terpicu, **atau**
  3. aturan BELI dan aturan TAHAN terpicu bersamaan (resolusi konflik konservatif).
* **`BELI`** hanya jika minimal satu aturan R1–R5 terpicu, tidak ada aturan R6–R10 terpicu, dan `Signal_Valid == True`.
* **Exit position** tidak menunggu sinyal harian, melainkan manajemen risiko berbasis ATR(14) yang dikunci saat sinyal BELI:
  * **Take Profit (TP)** = $\text{Harga Masuk} + (2.0 \times \text{ATR}_{14})$ — default, dapat diubah $1.0\times$–$6.0\times$.
  * **Stop Loss (SL)** = $\text{Harga Masuk} - (1.0 \times \text{ATR}_{14})$ — default, dapat diubah $0.5\times$–$4.0\times$.

---

## 3. Daftar Variabel yang Dihasilkan Modul

| Kategori | Kolom / Key | Rumus / Logika | Kegunaan |
| :--- | :--- | :--- | :--- |
| Indikator 1 | `RSI_14` / `rsi_14` | Wilder's Smoothing 14 hari (0–100) | Pemicu R1, R6; syarat `below_70` untuk R2/R4/R5 |
| Indikator 2 | `MACD_Hist` / `macd_hist` | $\text{EMA}_{12} - \text{EMA}_{26} - \text{Signal}_9$ | Pemicu R2 (cross up 0) dan R7 (cross down 0) |
| Indikator 3 | `BB_PctB` / `bb_pct_b` | $\frac{\text{Close} - \text{BB\_Lower}}{\text{BB\_Upper} - \text{BB\_Lower}}$ | Pemicu R3, R4, R5, R8, R9, R10 |
| Pendukung visual | `Volume_Ratio` / `volume_ratio` | $\frac{\text{Volume}}{\text{SMA}(\text{Volume}, 20)}$ | **Tidak dipakai aturan** (hanya untuk tampilan/analisis) |
| Filter tren | `Is_Uptrend` / `is_uptrend` | $\text{SMA}_{20} > \text{SMA}_{50}$ | Syarat pertama validasi sinyal |
| Filter NPMM | `Near_Local_Min` / `near_local_min` | $\frac{\text{Close} - \text{PriorLow}_N}{\text{PriorLow}_N} \le 0.03$ | Syarat kedua validasi sinyal |
| Referensi NPMM | `Local_Min_N` / `local_min_n` | $\min(\text{Low}_{t-N} \dots \text{Low}_{t-1})$ (**shift 1**) | Harga terendah N hari **sebelum** hari ini |
| Fakta Tahap 3 | `Signal_Valid` / `signal_valid` | `Is_Uptrend` $\land$ `Near_Local_Min` | Gerbang akhir: jika `False`, keputusan dipaksa TAHAN |
| Risiko | `ATR_14` / `atr_14` | Wilder's Smoothing True Range 14 hari | Dasar TP ($2\times$) dan SL ($1\times$) |

> **Catatan anti look-ahead:** `Local_Min_N` memakai `Low.rolling(N).min().shift(1)` sehingga `Low` hari ini tidak ikut menjadi acuan. Perhitungan ini identik dengan `validate_signals()` pada `src/signal_validation_backtest.py`, sehingga dashboard, evaluasi CLI, dan backtest menghasilkan status `Signal_Valid` yang sama.

---

## 4. Struktur Direktori & File Output

```text
storage_data/
├── 1_raw_incremental/                  # Cache data mentah (OHLCV)
│   ├── BBCA_raw_daily.csv
│   ├── BBRI_raw_daily.csv
│   └── TLKM_raw_daily.csv
│
├── 2_inference_ready/                  # Siap dipakai modul lain
│   ├── BBCA_clean_indicators.csv       # Historis 3 tahun + indikator (backtest & chart)
│   ├── BBCA_latest_facts.json          # Snapshot fakta hari terakhir (inference engine)
│   ├── BBRI_clean_indicators.csv
│   ├── BBRI_latest_facts.json
│   ├── TLKM_clean_indicators.csv
│   ├── TLKM_latest_facts.json
│   └── ALL_STOCKS_latest_facts.json    # Gabungan snapshot seluruh saham
│
├── 3_rule_evaluation/                  # Output run_evaluation.py
│   └── <CODE>_rule_eval.csv
│
└── 4_backtesting/                      # Output signal_validation_backtest.py
    ├── <CODE>_trades.csv
    ├── <CODE>_daily.csv
    └── <CODE>_atr_calibration.csv
```

---

## 5. Implementasi Kode

Kode sumber lengkap ada di **`data_indicators_engineers.py`** (root proyek). Bagian inti perhitungan filter validasi:

```python
# Filter Validasi Sinyal (Tahap 3: Tren Naik & Dekat Minimum Lokal NPMM)
data['Is_Uptrend'] = data['SMA_20'] > data['SMA_50']
data['Local_Min_N'] = data['Low'].rolling(window=npmm_window).min().shift(1)
data['Near_Local_Min'] = (
    (data['Close'] - data['Local_Min_N']) / data['Local_Min_N'] <= local_min_tol
)
data['Signal_Valid'] = data['Is_Uptrend'] & data['Near_Local_Min']
```

Struktur fakta JSON yang dihasilkan (`<CODE>_latest_facts.json`):

```json
{
  "metadata": { "ticker": "BBCA.JK", "code": "BBCA", "date": "YYYY-MM-DD",
                "status_data": "FINAL (EOD)" },
  "price_volume": { "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0 },
  "indicator_inputs": { "rsi_14": 0, "macd_hist": 0, "bb_pct_b": 0 },
  "previous_inputs":  { "rsi_14": 0, "macd_hist": 0, "bb_pct_b": 0 },
  "previous2_inputs": { "rsi_14": 0, "macd_hist": 0, "bb_pct_b": 0 },
  "validation_filter": { "sma_20": 0, "sma_50": 0, "is_uptrend": true,
                         "local_min_n": 0, "near_local_min": true,
                         "signal_valid": true },
  "risk_management": { "atr_14": 0,
                       "initial_tp_estimate": 0,
                       "initial_sl_estimate": 0 }
}
```

Dependensi: `yfinance`, `pandas`, `numpy`, `schedule`, `pytz` (lihat `requirements.txt`).

---

## 6. Panduan Integrasi untuk Modul Selanjutnya

### A. Inference Engine — membaca snapshot JSON + riwayat t-1/t-2

```python
import json
from rule_engine import infer

with open("storage_data/2_inference_ready/BBCA_latest_facts.json", "r") as f:
    facts = json.load(f)

result = infer(facts)
print(result["decision"], result["buy_rules_fired"], result["hold_rules_fired"])
print(result["events"])       # status pemicu RSI, MACD, %B
print(result["explanation"])  # narasi penalaran
```

`rule_engine.infer()` membaca `indicator_inputs` (fallback lama: `fuzzy_inputs`), `previous_inputs`, `previous2_inputs`, `validation_filter`, `risk_management`, dan `price_volume`.

### B. Backtesting & Visualisasi — membaca CSV historis

```python
import pandas as pd

df = pd.read_csv(
    "storage_data/2_inference_ready/BBCA_clean_indicators.csv",
    index_col="Date", parse_dates=True
)
print(df[["Close", "RSI_14", "MACD_Hist", "BB_PctB", "Signal_Valid", "ATR_14"]].tail())
```

Kolom yang tersedia sudah bersih dari NaN dan siap dipakai `evaluate_dataframe()`, `backtest()`, serta grafik dashboard.

### C. Perintah Terkait

```bash
python data_indicators_engineers.py          # perbarui CSV + JSON (scheduler 15 menit & 16:30 WIB)
python src/run_inference.py BBCA             # inferensi snapshot terakhir
python src/run_evaluation.py --all --save-csv
python src/signal_validation_backtest.py --all --save-details
```
