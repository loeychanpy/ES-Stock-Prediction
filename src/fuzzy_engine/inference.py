"""
Mesin inferensi Mamdani dengan forward chaining:
  - Implikasi : MIN (potong himpunan output di firing strength)
  - Agregasi  : MAX (gabungkan output tiap aturan)
  - Defuzzifikasi : CENTROID (titik berat kurva agregat)

Himpunan output "kekuatan sinyal beli" (skala 0 - 100):
  lemah, sedang, kuat.
"""

import numpy as np
from .knowledge_base import RULES
from .membership import triangular, trapezoidal


OUTPUT_RANGE = np.arange(0, 100.1, 1.0)


def _mu_lemah(x):  return trapezoidal(x, 0, 0, 30, 50)
def _mu_sedang(x): return triangular(x, 40, 60, 80)
def _mu_kuat(x):   return trapezoidal(x, 70, 85, 100, 100)

OUTPUT_SETS = {
    "lemah":  _mu_lemah,
    "sedang": _mu_sedang,
    "kuat":   _mu_kuat,
}


def apply_rules(fuzzified: dict) -> list:
    """Jalankan semua aturan, kembalikan daftar hasil firing strength."""
    results = []
    for rule in RULES:
        alpha = rule["antecedent"](fuzzified)
        results.append({
            "id": rule["id"],
            "description": rule["description"],
            "consequent": rule["consequent"],
            "firing_strength": round(float(alpha), 4),
        })
    return results


def aggregate(fired_rules: list) -> np.ndarray:
    """Agregasi MAX dari output aturan yang sudah diklip implikasi MIN."""
    aggregated = np.zeros_like(OUTPUT_RANGE)
    for rule in fired_rules:
        alpha = rule["firing_strength"]
        if alpha <= 0:
            continue
        mu_func = OUTPUT_SETS[rule["consequent"]]
        clipped = np.array([min(alpha, mu_func(x)) for x in OUTPUT_RANGE])
        aggregated = np.maximum(aggregated, clipped)
    return aggregated


def defuzzify_centroid(aggregated: np.ndarray) -> float:
    """Centroid / Center of Gravity: y* = sum(x * mu(x)) / sum(mu(x))."""
    total = aggregated.sum()
    if total == 0:
        return 0.0
    return float((OUTPUT_RANGE * aggregated).sum() / total)
