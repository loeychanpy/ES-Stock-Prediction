"""
Script CLI untuk menjalankan Fuzzy Inference Engine atas file JSON
yang dihasilkan modul Christian.

Pemakaian:
    python src/run_inference.py BBCA
    python src/run_inference.py BBCA BBRI TLKM
    python src/run_inference.py --all          # proses semua file yang tersedia
"""

import os
import sys
import json
import glob

from fuzzy_engine import infer


DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage_data", "2_inference_ready"
)


def run_for_code(code: str) -> dict:
    path = os.path.join(DATA_DIR, f"{code.upper()}_latest_facts.json")
    if not os.path.exists(path):
        print(f"[!] File tidak ditemukan: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        facts = json.load(f)
    return infer(facts)


def print_result(code: str, result: dict):
    if result is None:
        return
    print(f"\n=== {code.upper()} ===")
    print(f"Keputusan        : {result['decision']}")
    print(f"Skor Sinyal      : {result['signal_strength']}/100")
    print(f"Signal Valid     : {result['signal_valid']}")
    print(f"Entry / TP / SL  : {result['entry_price']} / {result['tp']} / {result['sl']}")
    print(f"\nAturan Terpicu   :")
    for r in result["triggered_rules"]:
        print(f"  {r['id']} ({r['consequent']:8s}, alpha={r['firing_strength']:.3f}) "
              f"{r['description']}")
    print(f"\nPenjelasan       : {result['explanation']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        files = sorted(glob.glob(os.path.join(DATA_DIR, "*_latest_facts.json")))
        if not files:
            print(f"[!] Tidak ada file di {DATA_DIR}")
            sys.exit(1)
        codes = [os.path.basename(f).replace("_latest_facts.json", "") for f in files]
    else:
        codes = sys.argv[1:]

    for code in codes:
        result = run_for_code(code)
        print_result(code, result)
