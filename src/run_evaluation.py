"""
CLI evaluasi Rule-Based Inference Engine atas data historis.

Pemakaian:
    python src/run_evaluation.py BBCA
    python src/run_evaluation.py BBCA BBRI TLKM
    python src/run_evaluation.py --all
    python src/run_evaluation.py BBCA --save-csv

Dengan --save-csv, hasil per-hari disimpan ke
    storage_data/3_rule_evaluation/<CODE>_rule_eval.csv
"""

import os
import sys
import glob

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rule_engine import evaluate_dataframe, print_summary  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "storage_data", "2_inference_ready")
OUT_DIR = os.path.join(ROOT, "storage_data", "3_rule_evaluation")


def evaluate_code(code: str, save_csv: bool = False) -> dict | None:
    csv_path = os.path.join(DATA_DIR, f"{code.upper()}_clean_indicators.csv")
    if not os.path.exists(csv_path):
        print(f"[!] CSV tidak ditemukan: {csv_path}")
        return None

    df = pd.read_csv(csv_path, index_col="Date", parse_dates=True)
    print(f"[OK] {code.upper()} dimuat: {len(df)} baris, "
          f"{df.index.min().date()} s.d {df.index.max().date()}")

    result = evaluate_dataframe(df)
    print_summary(code, result)

    if save_csv:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{code.upper()}_rule_eval.csv")
        result["per_row"].to_csv(out_path, index=False)
        print(f"\n[SAVE] Hasil per-hari: {out_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    save_csv = "--save-csv" in sys.argv
    if "--all" in sys.argv:
        files = sorted(glob.glob(os.path.join(DATA_DIR, "*_clean_indicators.csv")))
        if not files:
            print(f"[!] Tidak ada file CSV di {DATA_DIR}")
            sys.exit(1)
        codes = [os.path.basename(f).replace("_clean_indicators.csv", "") for f in files]
    else:
        codes = [a for a in sys.argv[1:] if not a.startswith("--")]

    for code in codes:
        evaluate_code(code, save_csv=save_csv)
