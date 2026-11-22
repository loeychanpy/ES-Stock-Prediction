# Stock Trading Expert System — Kelompok 8

Sistem Pakar rekomendasi perdagangan saham BEI/IDX berbasis aturan (**Pure Rule-Based**) dengan metode penalaran maju (**Forward Chaining**), deteksi kejadian teknikal tegas (*Event-Driven Indicator Crossing*), filter validasi tren & kedekatan harga terendah (*NPMM Proximity*), serta visualisasi interaktif bergaya **TradingView Supercharts**. Proyek Sistem Pakar, Teknik Informatika UKRIDA 2026.

---

## 👥 Anggota Tim & Pembagian Modul

| Anggota | Peran / Modul | Berkas & Folder Utama |
|---|---|---|
| **Christian** | Data Ingestion & Technical Indicators Engineer | `data_indicators_engineers.py` |
| **Janisha** | Rule-Based Inference Engine (Forward Chaining) | `src/rule_engine/` |
| **Felix** | Signal Validation (NPMM) & Event-Driven Backtesting | `src/signal_validation_backtest.py` |
| **Krisantus** | Web Application, TradingView Supercharts & Interactive Visualization | `src/web/` & `run_web.py` |

---

## 🔄 Alur Sistem & Data Pipeline

```
Yahoo Finance (yfinance)
         │
         ▼
[Modul Christian: data_indicators_engineers.py]
  - Preprocessing harga harian (OHLCV)
  - Kalkulasi Indikator: SMA 20/50, RSI 14, MACD, %B, ATR 14
  - Filter Validasi Tahap 3 (Tren SMA & Minimum Lokal NPMM)
         │
         ├────────────────────────────────────────┐
         ▼                                        ▼
storage_data/2_inference_ready/          storage_data/2_inference_ready/
  <CODE>_clean_indicators.csv (3 Thn)      <CODE>_latest_facts.json (Hari Terakhir)
         │                                        │
         │ (Historis t, t-1, t-2)                 │ (Snapshot EOD + t-1, t-2)
         ▼                                        ▼
[Modul Janisha: src/rule_engine/] <────────────────┘
  - indicator_events.py : Deteksi sentuhan & penembusan garis acuan
  - knowledge_base.py   : Basis Aturan R1 s.d R10
  - inference.py        : Forward Chaining & Resolusi Konflik
  - explainer.py        : Narasi Penjelasan Rekomendasi
         │
         ├─── Output: { decision, signal_valid, events, all_rules, tp, sl }
         │
         ├────────────────────────────────────────┐
         ▼                                        ▼
[Modul Felix: Backtesting]               [Modul Krisantus: Web App]
  - Evaluasi Proksimitas NPMM              - Dashboard Analisis Saham (Dynamic Config)
  - Simulasi Transaksi (TP/SL)             - TradingView Supercharts (Multi-Timeframe 1D/1W/1M)
  - Parameter: N-Days, Tol %, TP, SL       - Track Record Sinyal Terpicu (Trigger History)
  - storage_data/4_backtesting/            - Pane Khusus Indikator %B (0, 0.5, 1) & Aturan R1-R10
```

---

## 📊 Indikator Teknikal & Logika Pemicu (Event-Driven)

Sistem pakar ini **tidak menggunakan rentang angka statis atau logika fuzzy**, melainkan dipicu secara tegas (*crisp Boolean*) berdasarkan **peristiwa perpotongan (*crossing*) atau sentuhan (*touching*) garis acuan indikator** dengan membandingkan nilai hari ini ($t$) terhadap hari sebelumnya ($t-1$, $t-2$):

### 1. Relative Strength Index (RSI 14)
* **Menyentuh $\le 30$ dari atas** ($\text{RSI}_{t-1} > 30$ dan $\text{RSI}_t \le 30$): Indikasi jenuh jual (*oversold*), pemicu sinyal **BUY paling kuat**.
* **Zona Momentum ($30 < \text{RSI} < 70$ / selama $< 70$)**: Harga masih memiliki ruang gerak naik menuju 70. Berfungsi sebagai syarat pendukung untuk pemicu MACD dan %B.
* **Menyentuh $\ge 70$ dari bawah** ($\text{RSI}_{t-1} < 70$ dan $\text{RSI}_t \ge 70$): Indikasi jenuh beli (*overbought*), pemicu sinyal **TAHAN / Potensi Turun**.

### 2. MACD Histogram (12, 26, 9)
* **Pembalikan Merah $\rightarrow$ Hijau (Menembus garis 0 ke atas)** ($\text{Hist}_{t-1} \le 0 < \text{Hist}_t$): Terjadi pembalikan momentum dari tren turun ke tren naik $\rightarrow$ pemicu sinyal **BUY**.
* **Pembalikan Hijau $\rightarrow$ Merah (Menembus garis 0 ke bawah)** ($\text{Hist}_{t-1} \ge 0 > \text{Hist}_t$): Terjadi pembalikan momentum dari tren naik ke tren turun $\rightarrow$ pemicu sinyal **TAHAN / Turun**.

### 3. Indikator %B (Bollinger %B)
Indikator posisi relatif harga terhadap volatilitas pita dengan 3 garis acuan utama: **0.0** (garis bawah), **0.5** (garis tengah/pivot), dan **1.0** (garis atas):
* **Menyentuh garis $\le 0.0$ dari atas** ($\%B_{t-1} > 0$ dan $\%B_t \le 0$): Harga menyentuh batas bawah $\rightarrow$ indikasi **pantul naik (BUY)**.
* **Menembus garis $0.5$ ke atas** ($\%B_{t-1} < 0.5 \le \%B_t < 1.0$): Harga berhasil menembus garis tengah $\rightarrow$ indikasi **lanjut naik menuju garis 1.0 (BUY)**.
* **Memantul naik di garis $0.5$**: Harga turun mendekati $0.5$ lalu berbalik arah naik $\rightarrow$ garis tengah menjadi *support* pembalikan (**BUY**).
* **Menyentuh garis $\ge 1.0$ dari bawah** ($\%B_{t-1} < 1.0 \le \%B_t$): Harga menyentuh batas atas $\rightarrow$ indikasi **berbalik turun (TAHAN)**.
* **Menembus garis $0.5$ ke bawah** ($\%B_{t-1} > 0.5 \ge \%B_t > 0$): Harga jatuh melewati garis tengah $\rightarrow$ indikasi **lanjut turun menuju garis 0.0 (TAHAN)**.
* **Ditolak di garis $0.5$**: Harga naik mendekati $0.5$ lalu berbalik arah turun $\rightarrow$ garis tengah menjadi *resistance* (**TAHAN**).

### 4. Average True Range (ATR 14) — Manajemen Risiko Dinamis
Digunakan khusus untuk mengukur volatilitas pasar dan menetapkan target harga secara otomatis sesuai rasio *Risk-Reward* default:
* **Target Take Profit (TP)** = $\text{Entry Price} + (2.0 \times \text{ATR}_{14})$ *(default: $2.0\times\text{ATR}$, dapat diatur $1.0\times - 6.0\times$)*
* **Batas Stop Loss (SL)** = $\text{Entry Price} - (1.0 \times \text{ATR}_{14})$ *(default: $1.0\times\text{ATR}$, dapat diatur $0.5\times - 4.0\times$)*

---

## 📜 Basis Aturan IF–THEN (Knowledge Base: R1 – R10)

Inferensi menggunakan **Forward Chaining** berbasis pencocokan fakta (*pattern matching*):

| ID | Indikator | Aksi | Deskripsi Logika Aturan | Makna Pakar |
|---|---|---|---|---|
| **R1** | RSI | **BELI** | `IF RSI menyentuh 30 dari atas THEN BELI` | Harga mencapai titik oversold ekstrem, potensi pantulan balik naik paling kuat. |
| **R2** | MACD | **BELI** | `IF histogram MACD merah berubah hijau (menembus garis 0 ke atas) AND RSI < 70 THEN BELI` | Terjadi konfirmasi pembalikan momentum naik dan RSI masih memiliki ruang apresiasi. |
| **R3** | %B | **BELI** | `IF %B menyentuh garis 0 dari atas THEN BELI` | Harga menyentuh batas bawah %B, indikasi pantulan naik ke atas. |
| **R4** | %B | **BELI** | `IF %B menembus garis 0.5 ke atas AND RSI < 70 THEN BELI` | Harga menembus garis tengah 0.5, potensi akselerasi naik menuju garis 1.0. |
| **R5** | %B | **BELI** | `IF %B memantul naik di garis 0.5 AND RSI < 70 THEN BELI` | Garis tengah 0.5 berhasil diuji sebagai support dan harga berbalik menguat. |
| **R6** | RSI | **TAHAN** | `IF RSI menyentuh 70 dari bawah THEN TAHAN` | Harga mencapai area overbought, ruang kenaikan telah jenuh. |
| **R7** | MACD | **TAHAN** | `IF histogram MACD hijau berubah merah (menembus garis 0 ke bawah) THEN TAHAN` | Pembalikan momentum ke arah penurunan harga. |
| **R8** | %B | **TAHAN** | `IF %B menyentuh garis 1 dari bawah THEN TAHAN` | Harga menyentuh batas atas %B, potensi pembalikan arah turun. |
| **R9** | %B | **TAHAN** | `IF %B menembus garis 0.5 ke bawah THEN TAHAN` | Harga kehilangan support tengah, indikasi pelemahan lanjut ke garis 0.0. |
| **R10** | %B | **TAHAN** | `IF %B ditolak di garis 0.5 (berbalik turun) THEN TAHAN` | Garis tengah 0.5 gagal ditembus dan harga tertekan kembali ke bawah. |

### Mekanisme Resolusi Konflik
1. Jika ada aturan **BELI** yang terpicu (`R1`–`R5`) dan **tidak ada** aturan **TAHAN** yang terpicu $\rightarrow$ Rekomendasi: **BELI**.
2. Jika aturan **BELI** dan **TAHAN** terpicu bersamaan $\rightarrow$ Rekomendasi: **TAHAN** (prinsip manajemen risiko konservatif).
3. Jika tidak ada aturan beli yang terpicu $\rightarrow$ Rekomendasi: **TAHAN**.

---

## 🛡️ Filter Validasi Sinyal (Tahap 3: NPMM & Trend)

Meskipun aturan teknikal terpicu, sinyal beli hanya dieksekusi jika lolos **Filter Validasi Tahap 3** untuk menjamin prinsip *Buy Low in Uptrend*:
1. **Filter Tren (Uptrend Valid)**: $\text{SMA}_{20} > \text{SMA}_{50}$ (hanya bertransaksi searah tren makro).
2. **Filter Minimum Lokal (NPMM Proximity)**: Harga penutupan hari ini harus berada **dekat** dengan harga terendah ($N$-hari, default: 5 hari, konfigurabel 2–60 hari), diukur **dua arah** dengan toleransi $\pm 3\%$ (default: 3.0%, konfigurabel 0.5%–10.0%):
   $$\left| \text{Close}_t - \text{Prior N-Day Low} \right| \le \text{Prior N-Day Low} \times \text{near\_pct}$$
   Alasan dua arah: harga yang sudah naik terlalu jauh ($> +3\%$) berarti mengejar di pucuk ayunan (*swing peak*), sedangkan harga yang jatuh terlalu dalam ($< -3\%$) berarti level support $N$-hari sudah gagal menahan harga — keduanya bukan lagi "dekat minimum". Tembusan kecil ($-3\% \le \text{jarak} < 0$) justru dianggap *undercut* / *false breakdown* yang lazim menjadi titik pantulan.

---

## 🚀 Panduan Menjalankan Sistem

### 1. Instalasi Lingkungan & Dependensi
```bash
# Pastikan berada di folder project
pip install -r requirements.txt
```

### 2. Unduh & Perbarui Data Saham BEI
Mengambil data 3 tahun terakhir dari Yahoo Finance untuk saham acuan (BBCA, BBRI, TLKM) dan mengekspor CSV serta fakta snapshot JSON:
```bash
python data_indicators_engineers.py
```
*Output tersimpan di: `storage_data/2_inference_ready/`*

> Saat web app dijalankan (`run_web.py`), pembaruan data dilakukan otomatis oleh
> *background updater* di dalam proses web, jadi script ini tidak perlu dijalankan
> terpisah. Script tetap berguna untuk pengisian data awal (*backfill*) atau
> finalisasi manual.

### 3. Eksekusi Inferensi Sinyal Harian (EOD)
Menjalankan inferensi pakar pada data snapshot terakhir:
```bash
# Periksa satu saham tertentu
python src/run_inference.py BBCA

# Periksa beberapa saham
python src/run_inference.py BBCA BBRI TLKM

# Periksa seluruh saham yang tersedia
python src/run_inference.py --all
```

### 4. Evaluasi Historis Aturan Pakar (Rule Engine Evaluation)
Mengevaluasi keterpenuhan aturan `R1` s.d `R10` atas data historis 3 tahun:
```bash
python src/run_evaluation.py --all --save-csv
```
*Output evaluasi tersimpan di: `storage_data/3_rule_evaluation/<CODE>_rule_eval.csv`*

### 5. Simulasi Backtest Event-Driven Bebas Bias
Menjalankan simulasi transaksi historis dengan eksekusi Open H+1 dan validasi TP/SL berbasis ATR:
```bash
python src/signal_validation_backtest.py --all --save-details
```
*Output hasil transaksi dan kurva modal tersimpan di: `storage_data/4_backtesting/`*

### 6. Menjalankan Dashboard Web Interaktif
Aplikasi antarmuka pengguna berbasis Flask, TradingView Supercharts & Plotly Dark Mode:
```bash
python run_web.py
# Atau dengan opsi port:
python run_web.py --port 5000

# Ubah interval auto-fetch menjadi 5 menit:
python run_web.py --interval 5

# Matikan updater latar belakang:
python run_web.py --no-auto-update
```
Buka browser di: **`http://127.0.0.1:5000`**

#### Update otomatis & status pasar (tanpa refresh manual)
* **Status sesi bursa langsung** di bilah atas setiap halaman: `PRA-PEMBUKAAN`, `SESI 1`, `ISTIRAHAT`, `SESI 2`, `PASCA-PENUTUPAN`, `TUTUP`, atau `AKHIR PEKAN`, lengkap dengan jam WIB dan hitungan mundur ke event berikutnya.
* **Background updater** di dalam proses web mengunduh candle terbaru dari Yahoo Finance setiap **15 menit** selama sesi bursa, lalu menulis ulang CSV/JSON secara atomik (pembaca tidak pernah melihat file setengah jadi).
* **Finalisasi EOD otomatis** pukul **16:30 WIB** (status data berubah dari *SEMENTARA* menjadi *FINAL (EOD)*).
* **Halaman memuat ulang sendiri** ketika data berubah: JavaScript memantau `/api/status` tiap 15 detik dan membandingkan `data.version`; jika berubah, halaman di-reload dengan parameter (ticker, N-hari, toleransi, TP/SL) tetap sama. Tidak perlu menekan F5.
* **Tombol Perbarui** di bilah status memaksa unduhan saat itu juga (berguna di luar jam bursa).
* Reload otomatis ditunda bila pengguna sedang mengisi form atau membuka modal, agar input tidak hilang.

Endpoint pendukung: `GET /api/status` (status pasar + versi data) dan `POST /api/refresh` (minta update segera).

---

## 🌐 Tampilan & Fitur Web Application (Krisantus)

### 1. Dashboard Analisis Saham (`/dashboard`)
* **Konfigurasi Parameter Analisis Dinamis**:
  Form terintegrasi di bagian atas dashboard untuk menyesuaikan parameter secara *real-time*:
  - **N-Hari Min Low**: Rentang hari minimum lokal sebelumnya (default: `5` hari).
  - **Toleransi Min**: Batas kedekatan dua arah ($\pm$) harga terhadap harga terendah lokal (default: `3.0`%).
  - **Take Profit (TP)**: Pengali ATR untuk estimasi target laba (default: `2.0` $\times$ ATR).
  - **Stop Loss (SL)**: Pengali ATR untuk batas risiko proteksi modal (default: `1.0` $\times$ ATR).
  - **Panduan Parameter**: Tombol *collapsible* "Panduan parameter & indikator" di bawah form menjelaskan arti NPMM, toleransi dua arah, TP/SL, setelan tiap indikator, serta **akibat tiap nilai** untuk N-Hari, toleransi, TP, dan SL (mis. toleransi 2–3% direkomendasikan; 1% terlalu ketat, di atas 3% sinyal bertambah tetapi win rate/return turun dan drawdown membesar). Tertutup secara default dan status buka/tutupnya diingat saat halaman memuat ulang otomatis.
* **Rekomendasi Utama & Target Harga**:
  Badge sinyal tegas (**BELI** hijau atau **TAHAN** abu-abu), status lolos/tidaknya filter validasi Tahap 3 (Tren SMA20>50 & NPMM Proximity), serta target harga dinamis Entry, TP, dan SL.
* **Status Fakta & Pemicu Indikator**:
  Kartu metrik langsung untuk **RSI (14)**, **MACD Histogram**, dan **Indikator %B** (lengkap dengan nilai bar sebelumnya dan keterangan pemicu event). Baris kedua menampilkan metrik volatilitas **ATR (14)**, perbandingan **SMA 20/50**, dan **Minimum Lokal NPMM**.
* **Grafik Interaktif TradingView Supercharts (Default) & Toggle Plotly Classic**:
  - **Multi-Timeframe Candle Sebenarnya (Candle Resolution)**:
    - `1D` (Daily): 1 Lilin melambangkan pergerakan 1 Hari bursa.
    - `1W` (Weekly): 1 Lilin melambangkan akumulasi 1 Minggu bursa (Open awal minggu, High/Low seminggu, Close akhir minggu).
    - `1M` (Monthly): 1 Lilin melambangkan akumulasi 1 Bulan bursa.
    - *Indikator 1W/1M dihitung ulang dari OHLC hasil agregasi; 1D memakai indikator resmi modul Data Engineer!*
  - **Rentang Zoom Waktu Terpisah**: Tombol `1 Bulan`, `3 Bulan`, `6 Bulan`, `1 Tahun`, dan `Semua Data` untuk navigasi cepat.
  - **5 Sub-Pane Tersinkronisasi**:
    1. Candlestick OHLC + SMA 20 + SMA 50 + Marker Sinyal Terpicu.
    2. **Indikator %B murni** dilengkapi garis batas 1.0 (merah), garis tengah 0.5 (ungu), dan batas 0.0 (hijau).
    3. RSI 14 (garis 70 dan 30).
    4. MACD Line, Signal Line, dan Histogram warna (Hijau/Merah).
    5. ATR 14 (Area Volatilitas).
  - **Interaksi Autentik Supercharts**:
    - Scroll mouse pada chart: Zoom horizontal waktu/bar.
    - Drag pada chart: Panning menggeser riwayat data waktu.
    - Scroll / Drag pada sumbu harga kanan: Stretch & Compress skala harga vertikal.
    - Double-click pada sumbu harga: Auto-fit reset skala vertikal.
    - Garis vertikal crosshair menembus seluruh pane secara bersamaan dengan legend reaktif real-time.
* **Track Record Sinyal Terpicu (Trigger History)**:
  Tabel rekam jejak historis seluruh sinyal beli yang pernah terpicu berdasarkan parameter aktif, memuat tanggal, harga close, daftar aturan terpicu (`R1`–`R5`), nilai indikator (RSI, MACD, %B, ATR), target TP/SL, serta jarak persentase terhadap minimum lokal.
* **Panel Status Basis Aturan (Knowledge Base R1–R10)**:
  Kartu visual edukatif yang menguraikan status keaktifan tiap aturan IF–THEN beserta penjelasan logikanya.

### 2. Halaman Backtest & Evaluasi Historis (`/backtest`)
* Konfigurasi parameter simulasi dinamis ($N$-hari, toleransi minimum, pengali TP/SL ATR).
* Ringkasan performa portofolio: *Win Rate*, *Total Return*, *Max Drawdown*, *Profit Factor*, dan *Excess Return vs Buy & Hold*.
* **Grafik 6-Pane Terintegrasi**: Kurva Candlestick, Indikator %B (dengan marker transaksi entry & exit), RSI, MACD, ATR, serta Kurva Pertumbuhan Modal (*Equity Curve*).
* Audit transaksi mendalam: Tabel riwayat entry, exit, persentase return, dan alasan pembalikan aturan pakar saat sinyal terbit.

---

## 📦 Kontrak Data Inferensi (`src/rule_engine/engine.py`)

Fungsi utama inferensi dipanggil melalui:
```python
from rule_engine import infer

# facts = dictionary fakta (indicator_inputs, previous_inputs, validation_filter, risk_management, price_volume)
result = infer(facts)
```

Struktur respon dictionary:
```json
{
  "decision": "BELI",
  "signal_valid": true,
  "events": {
    "rsi": {
      "value": 28.5,
      "prev": 32.1,
      "touch_30_from_above": true,
      "status": "PEMICU BUY KUAT: RSI menyentuh 30 dari atas"
    },
    "macd": {
      "value": 1.45,
      "prev": -0.82,
      "cross_up_zero": true,
      "status": "PEMICU BUY: histogram merah berubah hijau (lewat garis 0 ke atas)"
    },
    "bb": {
      "value": 0.54,
      "prev": 0.48,
      "cross_up_05": true,
      "status": "PEMICU BUY: %B menembus 0.5 ke atas (lanjut naik ke garis 1)"
    },
    "has_previous": true
  },
  "all_rules": [
    {
      "id": "R1",
      "indicator": "RSI",
      "description": "IF RSI menyentuh 30 dari atas THEN BELI",
      "makna": "RSI turun menyentuh 30 (oversold): potensi harga berbalik naik, sinyal beli paling kuat.",
      "consequent": "BELI",
      "fired": true
    }
  ],
  "triggered_rules": [...],
  "buy_rules_fired": ["R1", "R2", "R4"],
  "hold_rules_fired": [],
  "explanation": "KEPUTUSAN BELI - pemicu aktif: R1 (...); R2 (...); R4 (...)",
  "entry_price": 5325.0,
  "tp": 5600.0,
  "sl": 5187.5
}
```

---

## 📁 Struktur Direktori Proyek

```
Code/
├── README.md                           # Dokumentasi komprehensif sistem pakar
├── data_indicators_engineers.py        # Pengolahan data & indikator (Christian)
├── run_web.py                          # Runner Flask Web App
├── requirements.txt                    # Dependensi Python
├── storage_data/
│   ├── 1_raw_incremental/              # Cache data mentah yfinance
│   ├── 2_inference_ready/              # File CSV indikator & JSON fakta snapshot
│   ├── 3_rule_evaluation/              # Hasil evaluasi historis basis aturan R1-R10
│   └── 4_backtesting/                  # Log transaksi backtest, kurva modal, kalibrasi
└── src/
    ├── rule_engine/                    # Mesin inferensi Forward Chaining (Janisha)
    │   ├── __init__.py                 # Interface publik modul engine
    │   ├── engine.py                   # Siklus inferensi utama infer()
    │   ├── indicator_events.py         # Deteksi event perpotongan & sentuhan garis
    │   ├── knowledge_base.py           # Basis aturan R1 s.d R10
    │   ├── inference.py                # Pencocokan aturan & resolusi konflik
    │   ├── explainer.py                # Narasi penalaran keputusan
    │   ├── facts.py                    # Helper pembentukan fakta (t, t-1, t-2)
    │   └── evaluator.py                # Analisis statistik frekuensi aturan historis
    ├── run_inference.py                # CLI uji inferensi EOD
    ├── run_evaluation.py               # CLI evaluasi aturan historis
    ├── signal_validation_backtest.py   # Backtesting event-driven & NPMM (Felix)
    └── web/                            # Flask Web App (Krisantus)
        ├── app.py                      # Router & Controller Flask (Dashboard & Backtest)
        ├── tradingview.py              # Visualisasi TradingView Supercharts (Lightweight Charts v4)
        ├── utils.py                    # Visualisasi Plotly Classic & helper pemuatan data
        ├── static/css/style.css        # Styling tema terminal dark mode & kontrol Supercharts
        └── templates/
            ├── base.html               # Layout induk terminal
            ├── dashboard.html          # Halaman dashboard analisis saham & riwayat sinyal
            └── backtest.html           # Halaman backtest & audit transaksi
```
