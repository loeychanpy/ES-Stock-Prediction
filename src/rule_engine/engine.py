"""
Entry point Rule-Based Inference Engine (Forward Chaining murni).

Format fakta (facts) yang diterima:
{
  "indicator_inputs": {"rsi_14": .., "macd_hist": .., "bb_pct_b": ..},   # hari ini (t)
  "previous_inputs":  {"rsi_14": .., "macd_hist": .., "bb_pct_b": ..},   # hari t-1
  "previous2_inputs": {"bb_pct_b": ..},                                  # hari t-2 (opsional)
  "validation_filter": {"signal_valid": bool, ...},
  "risk_management":  {"initial_tp_estimate": .., "initial_sl_estimate": ..},
  "price_volume":     {"close": .., ...}
}
Kunci lama "fuzzy_inputs" dari file JSON lama tetap dibaca sebagai indicator_inputs.
"""

from .indicator_events import detect_all_events
from .inference import apply_rules, decide_from_rules
from .explainer import build_explanation


def _indicator_inputs(facts: dict) -> dict:
    inputs = facts.get("indicator_inputs") or facts.get("fuzzy_inputs") or {}
    return {k: inputs[k] for k in ("rsi_14", "macd_hist", "bb_pct_b")}


def infer(facts: dict) -> dict:
    inputs = _indicator_inputs(facts)
    prev_inputs = facts.get("previous_inputs") or {}
    prev2_inputs = facts.get("previous2_inputs") or {}
    validation = facts.get("validation_filter", {})
    risk = facts.get("risk_management", {})
    price = facts.get("price_volume", {})

    # 1. Deteksi pemicu indikator (selalu dihitung agar bisa ditampilkan)
    events = detect_all_events(inputs, prev_inputs, prev2_inputs)

    # 2. Forward chaining: cocokkan fakta pemicu ke basis aturan
    rule_results = apply_rules(events)
    decision, buy_fired, hold_fired = decide_from_rules(rule_results)

    # 3. Filter validasi Tahap 3 (tren & minimum lokal) sebagai gerbang akhir
    signal_valid = bool(validation.get("signal_valid", False))
    if not signal_valid:
        decision = "TAHAN"

    explanation = build_explanation(decision, buy_fired, hold_fired,
                                    signal_valid, events["has_previous"])

    return {
        "decision": decision,
        "signal_valid": signal_valid,
        "events": events,
        "all_rules": rule_results,
        "triggered_rules": [r for r in rule_results if r["fired"]],
        "buy_rules_fired": [r["id"] for r in buy_fired],
        "hold_rules_fired": [r["id"] for r in hold_fired],
        "explanation": explanation,
        "entry_price": price.get("close"),
        "tp": risk.get("initial_tp_estimate") if decision == "BELI" else None,
        "sl": risk.get("initial_sl_estimate") if decision == "BELI" else None,
    }
