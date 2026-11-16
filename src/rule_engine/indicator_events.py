"""
Deteksi PEMICU (event) indikator teknikal - Pure Rule-Based.

Pemicu tidak didasarkan pada rentang angka, melainkan pada KEJADIAN garis
yang disentuh / dilewati, dengan membandingkan nilai hari ini (t) dengan
nilai hari sebelumnya (t-1) [dan t-2 untuk pola pantulan garis 0.5 %B].

1. RSI (14)
   - RSI menyentuh 30 dari atas  : RSI[t-1] > 30  dan RSI[t] <= 30  -> potensi BUY kuat
   - Zona momentum 30 < RSI < 70 : masih ada ruang naik menuju 70 (pendukung buy,
                                   bukan pemicu mandiri)
   - RSI menyentuh 70 dari bawah : RSI[t-1] < 70  dan RSI[t] >= 70  -> potensi turun

2. MACD Histogram
   - Merah -> Hijau (lewat garis 0 ke atas) : Hist[t-1] <= 0 dan Hist[t] > 0 -> BUY
   - Hijau -> Merah (lewat garis 0 ke bawah): Hist[t-1] >= 0 dan Hist[t] < 0 -> turun

3. Bollinger %B (garis 0, 0.5, 1)
   - Menyentuh garis 0 dari atas    : %B[t-1] > 0   dan %B[t] <= 0          -> pantul naik (BUY)
   - Menembus 0.5 ke atas           : %B[t-1] < 0.5 dan 0.5 <= %B[t] < 1    -> lanjut naik ke 1 (BUY)
   - Pantul naik di garis 0.5       : turun mendekati 0.5 dari atas (t-1) lalu naik lagi (t) -> BUY
   - Menyentuh garis 1 dari bawah   : %B[t-1] < 1   dan %B[t] >= 1          -> berbalik turun
   - Menembus 0.5 ke bawah          : %B[t-1] > 0.5 dan 0 < %B[t] <= 0.5    -> lanjut turun ke 0
   - Ditolak di garis 0.5           : naik mendekati 0.5 dari bawah (t-1) lalu turun lagi (t) -> turun
"""

import math

RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
BB_LOWER = 0.0
BB_MIDDLE = 0.5
BB_UPPER = 1.0
# Jarak maksimal dari garis 0.5 agar dianggap "menyentuh" garis tengah %B
BB_MIDDLE_TOUCH_TOL = 0.05


def _valid(*values) -> bool:
    """True jika semua nilai tersedia (bukan None / NaN)."""
    for v in values:
        if v is None:
            return False
        try:
            if math.isnan(float(v)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def detect_rsi_events(curr: float, prev: float | None) -> dict:
    has_prev = _valid(prev)
    touch_30 = has_prev and prev > RSI_OVERSOLD and curr <= RSI_OVERSOLD
    touch_70 = has_prev and prev < RSI_OVERBOUGHT and curr >= RSI_OVERBOUGHT
    momentum_zone = RSI_OVERSOLD < curr < RSI_OVERBOUGHT
    below_70 = curr < RSI_OVERBOUGHT

    if touch_30:
        status = "PEMICU BUY KUAT: RSI menyentuh 30 dari atas"
    elif touch_70:
        status = "PEMICU TURUN: RSI menyentuh 70 dari bawah"
    elif momentum_zone:
        status = "Momentum buy (30-70): masih ada ruang naik ke 70"
    elif curr <= RSI_OVERSOLD:
        status = "Masih di area oversold (<= 30)"
    else:
        status = "Overbought (>= 70): tidak ada ruang naik"

    return {
        "value": round(float(curr), 4),
        "prev": round(float(prev), 4) if has_prev else None,
        "touch_30_from_above": bool(touch_30),
        "touch_70_from_below": bool(touch_70),
        "momentum_zone": bool(momentum_zone),
        "below_70": bool(below_70),
        "status": status,
    }


def detect_macd_events(curr: float, prev: float | None) -> dict:
    has_prev = _valid(prev)
    cross_up = has_prev and prev <= 0.0 < curr
    cross_down = has_prev and prev >= 0.0 > curr

    if cross_up:
        status = "PEMICU BUY: histogram merah berubah hijau (lewat garis 0 ke atas)"
    elif cross_down:
        status = "PEMICU TURUN: histogram hijau berubah merah (lewat garis 0 ke bawah)"
    elif curr > 0:
        status = "Histogram hijau (belum ada pembalikan baru)"
    else:
        status = "Histogram merah (belum ada pembalikan baru)"

    return {
        "value": round(float(curr), 4),
        "prev": round(float(prev), 4) if has_prev else None,
        "cross_up_zero": bool(cross_up),
        "cross_down_zero": bool(cross_down),
        "status": status,
    }


def detect_bb_events(curr: float, prev: float | None, prev2: float | None = None) -> dict:
    has_prev = _valid(prev)
    has_prev2 = has_prev and _valid(prev2)

    touch_0 = has_prev and prev > BB_LOWER and curr <= BB_LOWER
    touch_1 = has_prev and prev < BB_UPPER and curr >= BB_UPPER
    cross_up_05 = has_prev and prev < BB_MIDDLE <= curr < BB_UPPER
    cross_down_05 = has_prev and prev > BB_MIDDLE >= curr > BB_LOWER

    # Pantulan di garis tengah 0.5 (menyentuh tapi tidak tembus, lalu berbalik arah)
    bounce_up_05 = (
        has_prev2
        and prev2 > prev                                   # sebelumnya turun mendekati 0.5
        and BB_MIDDLE < prev <= BB_MIDDLE + BB_MIDDLE_TOUCH_TOL
        and curr > prev                                    # hari ini berbalik naik
    )
    reject_down_05 = (
        has_prev2
        and prev2 < prev                                   # sebelumnya naik mendekati 0.5
        and BB_MIDDLE - BB_MIDDLE_TOUCH_TOL <= prev < BB_MIDDLE
        and curr < prev                                    # hari ini berbalik turun
    )

    if touch_0:
        status = "PEMICU BUY: %B menyentuh garis 0 (indikasi pantul naik)"
    elif cross_up_05:
        status = "PEMICU BUY: %B menembus 0.5 ke atas (lanjut naik ke garis 1)"
    elif bounce_up_05:
        status = "PEMICU BUY: %B memantul naik di garis 0.5"
    elif touch_1:
        status = "PEMICU TURUN: %B menyentuh garis 1 (indikasi berbalik turun)"
    elif cross_down_05:
        status = "PEMICU TURUN: %B menembus 0.5 ke bawah (lanjut turun ke garis 0)"
    elif reject_down_05:
        status = "PEMICU TURUN: %B ditolak di garis 0.5 (berbalik turun)"
    else:
        status = "Tidak ada garis 0 / 0.5 / 1 yang disentuh hari ini"

    return {
        "value": round(float(curr), 4),
        "prev": round(float(prev), 4) if has_prev else None,
        "touch_0_from_above": bool(touch_0),
        "cross_up_05": bool(cross_up_05),
        "bounce_up_05": bool(bounce_up_05),
        "touch_1_from_below": bool(touch_1),
        "cross_down_05": bool(cross_down_05),
        "reject_down_05": bool(reject_down_05),
        "status": status,
    }


def detect_all_events(inputs: dict, prev_inputs: dict | None, prev2_inputs: dict | None = None) -> dict:
    """Deteksi seluruh pemicu dari 3 indikator (RSI, MACD Histogram, %B)."""
    prev_inputs = prev_inputs or {}
    prev2_inputs = prev2_inputs or {}
    return {
        "rsi": detect_rsi_events(inputs["rsi_14"], prev_inputs.get("rsi_14")),
        "macd": detect_macd_events(inputs["macd_hist"], prev_inputs.get("macd_hist")),
        "bb": detect_bb_events(inputs["bb_pct_b"], prev_inputs.get("bb_pct_b"),
                               prev2_inputs.get("bb_pct_b")),
        "has_previous": bool(prev_inputs),
    }
