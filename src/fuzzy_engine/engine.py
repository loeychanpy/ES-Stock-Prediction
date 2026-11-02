"""
Entry point modul Fuzzy Inference Engine.

Mengacu laporan METODE & DATA butir 4:
  "Inference engine berjalan maju dari fakta nilai indikator, lalu status
   sinyal (tahap 3), kekuatan sinyal, dan terakhir keputusan. Aturan fuzzy
   dievaluasi HANYA BILA SINYAL VALID, dengan AND = min, OR = max, implikasi
   min, agregasi max, dan defuzzifikasi centroid. Kekuatan sinyal minimal 70
   yang lolos tahap 3 menghasilkan BELI, selain itu TAHAN."

Pemakaian:
    from fuzzy_engine import infer
    result = infer(facts)   # facts = dict dari file JSON Christian
"""

from .fuzzifier import fuzzify_all
from .inference import apply_rules, aggregate, defuzzify_centroid
from .explainer import filter_triggered, build_explanation


BUY_THRESHOLD = 70.0   # ambang kekuatan sinyal untuk BELI (sesuai laporan)


def infer(facts: dict) -> dict:
    """Siklus inferensi forward chaining lengkap atas fakta harian satu saham."""
    fuzzy_inputs = facts["fuzzy_inputs"]
    validation = facts["validation_filter"]
    risk = facts["risk_management"]
    price = facts["price_volume"]

    # ---------- 1. Fakta nilai indikator -> cek status sinyal (tahap 3) ----------
    signal_valid = bool(validation.get("signal_valid", False))

    # ---------- 2. Short-circuit: aturan fuzzy dievaluasi HANYA bila sinyal valid ----------
    if not signal_valid:
        return {
            "decision": "TAHAN",
            "signal_strength": 0.0,
            "triggered_rules": [],
            "all_rules": [],
            "fuzzified_inputs": {},
            "explanation": (
                "Sinyal tidak valid (filter Tahap 3 gagal): tren tidak naik "
                "atau harga tidak dekat minimum lokal. Aturan fuzzy tidak "
                "dievaluasi — rekomendasi TAHAN."
            ),
            "signal_valid": False,
            "entry_price": price.get("close"),
            "tp": None,
            "sl": None,
        }

    # ---------- 3. Fuzzifikasi 4 input ----------
    fuzzified = fuzzify_all(fuzzy_inputs)

    # ---------- 4. Forward chaining: evaluasi R1-R4 ----------
    fired_rules = apply_rules(fuzzified)

    # ---------- 5. Agregasi + defuzzifikasi centroid ----------
    aggregated = aggregate(fired_rules)
    signal_score = defuzzify_centroid(aggregated)

    # ---------- 6. Keputusan: BELI jika skor >= 70, selain itu TAHAN ----------
    decision = "BELI" if signal_score >= BUY_THRESHOLD else "TAHAN"

    # ---------- 7. Penjelasan ----------
    triggered = filter_triggered(fired_rules)
    explanation = build_explanation(signal_score, triggered, signal_valid=True)

    return {
        "decision": decision,
        "signal_strength": round(signal_score, 2),
        "triggered_rules": triggered,
        "all_rules": fired_rules,
        "fuzzified_inputs": {
            k: {s: round(v, 4) for s, v in sets.items()}
            for k, sets in fuzzified.items()
        },
        "explanation": explanation,
        "signal_valid": True,
        # TP & SL hanya diterbitkan saat keputusan BELI (sesuai laporan OUTPUT)
        "entry_price": price.get("close"),
        "tp": risk.get("initial_tp_estimate") if decision == "BELI" else None,
        "sl": risk.get("initial_sl_estimate") if decision == "BELI" else None,
    }
