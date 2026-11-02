"""
Evaluasi model Fuzzy Inference Engine atas data historis.

Berbeda dengan backtesting Krisantus (yang mengukur kinerja TRADING:
win rate, return, drawdown setelah fee), modul ini mengukur PERILAKU
MODEL FUZZY itu sendiri:

  1. Distribusi keputusan (% BELI vs % TAHAN)
  2. Rate kelolosan filter validasi (Signal_Valid)
  3. Statistik skor kekuatan sinyal (mean, median, min, max, std)
  4. Firing frequency tiap aturan R1-R4 (seberapa sering teraktifkan)
  5. Rata-rata firing strength per aturan saat aktif
  6. Distribusi himpunan output yang menang (lemah/sedang/kuat)

Hasil ini berguna untuk:
  - Validasi apakah membership function sudah terkalibrasi
    (aturan R1 tidak pernah terpicu -> ambang MACD terlalu ketat, dll)
  - Diserahkan ke Krisantus sebagai bahan backtesting lanjutan
  - Dilampirkan di laporan analisa model
"""

import pandas as pd
import numpy as np

from .engine import infer


def _row_to_facts(row: pd.Series, atr_tp_mult: float = 3.0, atr_sl_mult: float = 1.5) -> dict:
    """Konversi satu baris DataFrame hasil Christian jadi dict facts."""
    close = float(row["Close"])
    atr = float(row["ATR_14"])
    return {
        "fuzzy_inputs": {
            "rsi_14":       float(row["RSI_14"]),
            "macd_hist":    float(row["MACD_Hist"]),
            "bb_pct_b":     float(row["BB_PctB"]),
            "volume_ratio": float(row["Volume_Ratio"]),
        },
        "validation_filter": {
            "signal_valid": bool(row["Signal_Valid"]),
        },
        "risk_management": {
            "initial_tp_estimate": round(close + atr_tp_mult * atr, 2),
            "initial_sl_estimate": round(close - atr_sl_mult * atr, 2),
        },
        "price_volume": {
            "close": close,
            "open":  float(row["Open"]),
            "high":  float(row["High"]),
            "low":   float(row["Low"]),
            "volume": int(row["Volume"]),
        },
    }


def evaluate_dataframe(df: pd.DataFrame) -> dict:
    """
    Jalankan fuzzy engine atas tiap baris df, hitung agregat statistiknya.

    Return:
        {
          "n_rows": int, "n_valid": int, "valid_rate": float,
          "n_beli": int, "n_tahan": int, "beli_rate": float,
          "score_stats": {mean, median, min, max, std},
          "score_stats_valid_only": {...},
          "rule_firing": {
             "R1": {"fire_rate", "mean_alpha_when_fire", "n_strong_fire"}, ...
          },
          "consequent_dist": {"kuat": n, "sedang": n, "lemah": n},
          "per_row": DataFrame[date, decision, score, signal_valid, R1, R2, R3, R4]
        }
    """
    rows_out = []
    rule_alphas = {"R1": [], "R2": [], "R3": [], "R4": []}
    consequent_count = {"kuat": 0, "sedang": 0, "lemah": 0}
    STRONG_FIRE_THRESHOLD = 0.5

    for date, row in df.iterrows():
        facts = _row_to_facts(row)
        result = infer(facts)

        # catat per-row untuk CSV detail
        row_record = {
            "date": date,
            "close": facts["price_volume"]["close"],
            "signal_valid": result["signal_valid"],
            "decision": result["decision"],
            "score": result["signal_strength"],
        }

        # jika sinyal valid, catat firing per aturan + himpunan output pemenang
        if result["signal_valid"] and result["all_rules"]:
            winner_consequent = None
            winner_alpha = -1
            for rule in result["all_rules"]:
                rid = rule["id"]
                alpha = rule["firing_strength"]
                row_record[rid] = alpha
                rule_alphas[rid].append(alpha)
                if alpha > winner_alpha:
                    winner_alpha = alpha
                    winner_consequent = rule["consequent"]
            if winner_alpha > 0 and winner_consequent:
                consequent_count[winner_consequent] += 1
        else:
            for rid in ["R1", "R2", "R3", "R4"]:
                row_record[rid] = 0.0

        rows_out.append(row_record)

    per_row = pd.DataFrame(rows_out)

    n = len(per_row)
    n_valid = int(per_row["signal_valid"].sum())
    n_beli = int((per_row["decision"] == "BELI").sum())
    n_tahan = n - n_beli

    def stats(series):
        if len(series) == 0:
            return {"mean": 0, "median": 0, "min": 0, "max": 0, "std": 0}
        return {
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "std": round(float(series.std()), 2),
        }

    rule_firing = {}
    for rid, alphas in rule_alphas.items():
        arr = np.array(alphas) if alphas else np.array([0.0])
        fired = arr[arr > 0]
        strong_fired = arr[arr >= STRONG_FIRE_THRESHOLD]
        rule_firing[rid] = {
            "fire_rate":           round(len(fired) / max(len(arr), 1), 4),
            "strong_fire_rate":    round(len(strong_fired) / max(len(arr), 1), 4),
            "mean_alpha_when_fire": round(float(fired.mean()), 4) if len(fired) else 0.0,
        }

    return {
        "n_rows": n,
        "n_valid": n_valid,
        "valid_rate": round(n_valid / max(n, 1), 4),
        "n_beli": n_beli,
        "n_tahan": n_tahan,
        "beli_rate": round(n_beli / max(n, 1), 4),
        "score_stats": stats(per_row["score"]),
        "score_stats_valid_only": stats(per_row.loc[per_row["signal_valid"], "score"]),
        "rule_firing": rule_firing,
        "consequent_dist": consequent_count,
        "per_row": per_row,
    }


def print_summary(code: str, result: dict):
    """Cetak ringkasan evaluasi ke console."""
    print(f"\n{'='*60}\nEVALUASI MODEL FUZZY - {code.upper()}\n{'='*60}")
    print(f"Jumlah hari    : {result['n_rows']}")
    print(f"Sinyal valid   : {result['n_valid']} ({result['valid_rate']*100:.1f}%)")
    print(f"Keputusan BELI : {result['n_beli']} ({result['beli_rate']*100:.1f}%)")
    print(f"Keputusan TAHAN: {result['n_tahan']}")

    print(f"\nSkor kekuatan sinyal (semua hari):")
    s = result["score_stats"]
    print(f"  mean={s['mean']}  median={s['median']}  min={s['min']}  max={s['max']}  std={s['std']}")

    print(f"\nSkor kekuatan sinyal (hanya sinyal valid):")
    s = result["score_stats_valid_only"]
    print(f"  mean={s['mean']}  median={s['median']}  min={s['min']}  max={s['max']}  std={s['std']}")

    print(f"\nFiring aturan (dari hari sinyal valid):")
    print(f"  {'Aturan':<6} {'fire_rate':>12} {'strong_fire':>12} {'mean_alpha':>12}")
    for rid, rf in result["rule_firing"].items():
        print(f"  {rid:<6} {rf['fire_rate']*100:>11.1f}% "
              f"{rf['strong_fire_rate']*100:>11.1f}% {rf['mean_alpha_when_fire']:>12.4f}")

    print(f"\nDistribusi himpunan output pemenang:")
    for k, v in result["consequent_dist"].items():
        print(f"  {k:<8}: {v}")

    # Diagnostik: aturan yang tidak pernah terpicu
    dead_rules = [rid for rid, rf in result["rule_firing"].items() if rf["fire_rate"] == 0]
    if dead_rules:
        print(f"\n[DIAGNOSTIK] Aturan tidak pernah terpicu: {dead_rules}")
        print(f"             -> Pertimbangkan kalibrasi membership function.")
