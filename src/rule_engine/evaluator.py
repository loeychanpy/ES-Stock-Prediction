"""
Evaluasi Rule-Based Inference Engine atas data historis.

Mengukur:
  1. Distribusi keputusan (BELI vs TAHAN)
  2. Jumlah hari lolos filter validasi (Signal_Valid)
  3. Frekuensi terpicunya tiap aturan R1-R10
"""

import pandas as pd

from .engine import infer
from .facts import build_facts
from .knowledge_base import ALL_RULE_IDS


def evaluate_dataframe(df: pd.DataFrame) -> dict:
    df = df.sort_index()
    rows_out = []
    for pos in range(len(df)):
        row = df.iloc[pos]
        facts = build_facts(df, pos, bool(row.get("Signal_Valid", False)))
        if not facts["indicator_inputs"]:
            continue  # masa warm-up indikator
        result = infer(facts)
        record = {
            "date": df.index[pos],
            "close": facts["price_volume"]["close"],
            "rsi_14": facts["indicator_inputs"]["rsi_14"],
            "macd_hist": facts["indicator_inputs"]["macd_hist"],
            "bb_pct_b": facts["indicator_inputs"]["bb_pct_b"],
            "signal_valid": result["signal_valid"],
            "decision": result["decision"],
            "buy_rules": ",".join(result["buy_rules_fired"]),
            "hold_rules": ",".join(result["hold_rules_fired"]),
        }
        for r in result["all_rules"]:
            record[r["id"]] = int(r["fired"])
        rows_out.append(record)

    per_row = pd.DataFrame(rows_out)
    n = len(per_row)
    n_valid = int(per_row["signal_valid"].sum()) if n else 0
    n_beli = int((per_row["decision"] == "BELI").sum()) if n else 0

    rule_firing = {}
    for rid in ALL_RULE_IDS:
        all_days = int(per_row[rid].sum()) if n else 0
        valid_days = int(per_row.loc[per_row["signal_valid"], rid].sum()) if n else 0
        rule_firing[rid] = {"fired_all_days": all_days, "fired_valid_days": valid_days}

    return {
        "n_rows": n,
        "n_valid": n_valid,
        "valid_rate": round(n_valid / max(n, 1), 4),
        "n_beli": n_beli,
        "n_tahan": n - n_beli,
        "beli_rate": round(n_beli / max(n, 1), 4),
        "rule_firing": rule_firing,
        "per_row": per_row,
    }


def print_summary(code: str, result: dict):
    print(f"\n{'=' * 60}\nEVALUASI SISTEM PAKAR RULE-BASED - {code.upper()}\n{'=' * 60}")
    print(f"Jumlah hari     : {result['n_rows']}")
    print(f"Sinyal valid    : {result['n_valid']} ({result['valid_rate'] * 100:.1f}%)")
    print(f"Keputusan BELI  : {result['n_beli']} ({result['beli_rate'] * 100:.1f}%)")
    print(f"Keputusan TAHAN : {result['n_tahan']}")
    print("\nFrekuensi aturan terpicu:")
    print(f"  {'Aturan':<7}{'Semua hari':>12}{'Hari valid':>12}")
    for rid, rf in result["rule_firing"].items():
        print(f"  {rid:<7}{rf['fired_all_days']:>12}{rf['fired_valid_days']:>12}")
