# Stock Trading Expert System — Kelompok 8

Sistem pakar rekomendasi saham BEI/IDX menggunakan **Fuzzy Logic (Mamdani)** +
**Forward Chaining**. UTS Sistem Pakar, UKRIDA 2026.

## Anggota & Modul

| Anggota | Modul | Folder |
|---|---|---|
| Christian | Data & Indicators Engineer | `src/data_indicators_engineer.py` |
| Janisha | Fuzzy Inference Engine | `src/fuzzy_engine/` |
| Felix | Signal Validation & Backtesting | TBD |
| Krisantus | Web App & Visualization | TBD |

## Alur Data

```
Yahoo Finance (yfinance)
        v
Christian: data_indicators_engineer.py
        v
storage_data/2_inference_ready/
  +-- BBCA_latest_facts.json  (fakta hari terakhir)
  +-- BBCA_clean_indicators.csv  (historis 3 tahun)
        v
Janisha: fuzzy_engine/
  - fuzzifier.py      (4 input -> himpunan fuzzy)
  - knowledge_base.py (aturan R1-R5)
  - inference.py      (Mamdani: implikasi MIN, agregasi MAX, centroid)
  - explainer.py      (narasi aturan terpicu)
        v
   { decision, signal_strength, triggered_rules, explanation, tp, sl }
        v
 Felix (backtest) + Krisantus (web app) membaca output di atas
```

## Cara jalankan (modul Fuzzy Inference)

```bash
pip install -r requirements.txt

# 1. Jalankan modul Christian dulu (biar file JSON terbentuk)
python src/data_indicators_engineer.py
# Tunggu storage_data/2_inference_ready/ terisi, lalu Ctrl+C

# 2. Jalankan fuzzy inference engine
python src/run_inference.py BBCA
python src/run_inference.py BBCA BBRI TLKM
python src/run_inference.py --all
```

## Kontrak output modul Fuzzy Inference 

```python
from fuzzy_engine import infer
result = infer(facts)   # facts = dict dari file JSON Christian

# result:
{
    "decision": "BELI" | "TAHAN",
    "signal_strength": float,            # 0-100 (hasil defuzzifikasi centroid)
    "triggered_rules": [
        {"id": "R1", "description": "...", "consequent": "strong",
         "firing_strength": 0.82}
    ],
    "all_rules": [...],                  # semua aturan + alpha (buat debugging)
    "fuzzified_inputs": {...},           # buat visualisasi grafik keanggotaan
    "explanation": str,
    "signal_valid": bool,
    "entry_price": float,
    "tp": float,
    "sl": float
}
```
