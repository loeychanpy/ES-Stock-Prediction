"""
Fungsi keanggotaan (membership functions) untuk fuzzifikasi.
Dua bentuk standar: segitiga (triangular) dan trapesium (trapezoidal).
"""


def triangular(x: float, a: float, b: float, c: float) -> float:
    """
    Fungsi segitiga dengan puncak di b.
      a: titik kiri (membership = 0)
      b: puncak    (membership = 1)
      c: titik kanan (membership = 0)
    """
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
    """
    Fungsi trapesium dengan plateau di [b, c].
      a: titik kiri (membership = 0)
      b: awal plateau (membership = 1)
      c: akhir plateau (membership = 1)
      d: titik kanan (membership = 0)
    """
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)
