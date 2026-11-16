"""
Rule-Based Inference Engine (Forward Chaining) - Kelompok 8

Indikator: RSI (14), MACD Histogram, Bollinger %B.
Pemicu berupa kejadian garis disentuh / dilewati (lihat indicator_events.py).

Expose:
  infer(facts)                     - inferensi satu snapshot fakta
  build_facts(df, pos, valid)      - susun fakta dari DataFrame (t, t-1, t-2)
  attach_previous_inputs(facts,df) - lengkapi facts JSON dengan nilai t-1, t-2
  evaluate_dataframe(df)           - evaluasi atas data historis
  print_summary(code, result)      - ringkasan evaluasi ke console
"""
from .engine import infer
from .facts import build_facts, attach_previous_inputs
from .evaluator import evaluate_dataframe, print_summary

__all__ = ["infer", "build_facts", "attach_previous_inputs",
           "evaluate_dataframe", "print_summary"]
