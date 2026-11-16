"""
Mesin Inferensi Forward Chaining (Pure Rule-Based).

Alur:
  1. Fakta pemicu indikator (hasil indicator_events) dicocokkan ke setiap aturan.
  2. Aturan yang kondisinya True dinyatakan TERPICU (fired).
  3. Resolusi konflik:
       - Ada aturan BELI terpicu dan TIDAK ada aturan TAHAN terpicu -> BELI
       - Aturan BELI dan TAHAN terpicu bersamaan                   -> TAHAN (konservatif)
       - Tidak ada aturan BELI terpicu                             -> TAHAN
"""

from .knowledge_base import RULES


def apply_rules(events: dict) -> list:
    """Evaluasi seluruh aturan; kembalikan status True/False tiap aturan."""
    results = []
    for rule in RULES:
        fired = bool(rule["condition"](events))
        results.append({
            "id": rule["id"],
            "indicator": rule["indicator"],
            "description": rule["description"],
            "makna": rule["makna"],
            "consequent": rule["consequent"],
            "fired": fired,
        })
    return results


def decide_from_rules(rule_results: list) -> tuple[str, list, list]:
    """Tentukan keputusan akhir dari aturan yang terpicu."""
    buy_fired = [r for r in rule_results if r["fired"] and r["consequent"] == "BELI"]
    hold_fired = [r for r in rule_results if r["fired"] and r["consequent"] == "TAHAN"]
    decision = "BELI" if buy_fired and not hold_fired else "TAHAN"
    return decision, buy_fired, hold_fired
