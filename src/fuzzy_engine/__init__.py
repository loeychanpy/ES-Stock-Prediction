"""
Fuzzy Inference Engine - Janisha (Kelompok 8)

Expose:
  infer(facts)                   - inferensi satu snapshot fakta
  evaluate_dataframe(df)         - evaluasi model atas data historis
  print_summary(code, result)    - ringkasan evaluasi ke console
"""
from .engine import infer
from .evaluator import evaluate_dataframe, print_summary

__all__ = ["infer", "evaluate_dataframe", "print_summary"]
