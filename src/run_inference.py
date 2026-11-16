"""
CLI untuk menjalankan Rule-Based Inference Engine pada data hari terakhir.

Pemakaian:
    python src/run_inference.py BBCA
    python src/run_inference.py BBCA BBRI TLKM
    python src/run_inference.py --all
"""

import os
import sys
import json
import glob

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rule_engine import infer, attach_previous_inputs  # noqa: E402

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage_data", "2_inference_ready"
)


def run_for_code(code: str) -> dict | None:
    path = os.path.join(DATA_DIR, f"{code.upper()}_latest_facts.json")
    if not os.path.exists(path):
        print(f"[!] File tidak ditemukan: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        facts = json.load(f)
    csv_path = os.path.join(DATA_DIR, f"{code.upper()}_clean_indicators.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, index_col="Date", parse_dates=True)
        facts = attach_previous_inputs(facts, df)
    return infer(facts)


def print_result(code: str, result: dict):
    if result is None:
        return
    print(f"\n=== {code.upper()} ===")
    print(f"Keputusan        : {result['decision']}")
    print(f"Signal Valid     : {result['signal_valid']}")
    print(f"Entry / TP / SL  : {result['entry_price']} / {result['tp']} / {result['sl']}")
    ev = result["events"]
    print(f"RSI              : {ev['rsi']['status']}")
    print(f"MACD Histogram   : {ev['macd']['status']}")
    print(f"%B               : {ev['bb']['status']}")
    print("\nAturan Terpicu   :")
    for r in result["triggered_rules"] or []:
        print(f"  {r['id']:<4} ({r['consequent']}) {r['description']}")
    if not result["triggered_rules"]:
        print("  (tidak ada)")
    print(f"\nPenjelasan       : {result['explanation']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        files = sorted(glob.glob(os.path.join(DATA_DIR, "*_latest_facts.json")))
        codes = [os.path.basename(f).replace("_latest_facts.json", "") for f in files
                 if not os.path.basename(f).startswith("ALL_STOCKS")]
    else:
        codes = sys.argv[1:]

    for code in codes:
        print_result(code, run_for_code(code))
