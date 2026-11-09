"""
Fuzzifikasi: mengubah nilai crisp indikator teknikal menjadi derajat
keanggotaan pada tiap himpunan fuzzy.

Mengacu laporan Metode & Data:
  "Tiap input dipetakan ke tiga himpunan fuzzy (fungsi segitiga dan
   trapesium; RSI di bawah 30 sepenuhnya rendah [3])."

Empat input (sesuai output modul Data & Indicators Engineer / Christian):
  1. RSI_14         -> {rendah, sedang, tinggi}
  2. MACD_Hist      -> {negatif, netral, positif}
  3. BB_PctB        -> {rendah, sedang, tinggi}
  4. Volume_Ratio   -> {rendah, normal, tinggi}
"""

from .membership import triangular, trapezoidal


def fuzzify_rsi(rsi: float) -> dict:
    """
    RSI (0 - 100).
      - 'rendah' penuh (membership=1) untuk RSI <= 30 [sesuai laporan ref 3],
        dan meluruh hingga 55 untuk menangkap koreksi (pullback) pada saat uptrend.
      - 'tinggi' penuh (membership=1) untuk RSI >= 70 [overbought].
    """
    return {
        "rendah": trapezoidal(rsi, 0, 0, 30, 55),
        "sedang": triangular(rsi, 35, 52, 68),
        "tinggi": trapezoidal(rsi, 60, 70, 100, 100),
    }


def fuzzify_macd_hist(macd_hist: float) -> dict:
    """
    MACD Histogram = MACD_Line - MACD_Signal.
    Positif = momentum naik (golden cross); negatif = momentum turun.
    Batas dikalibrasi terhadap skala harga saham BEI/IDX (dalam Rupiah):
      - 'negatif' aktif saat pelemahan jelas (< -5.0, penuh <= -25.0)
      - 'netral' di sekitar garis nol (-10.0 s.d 10.0)
      - 'positif' aktif saat histogram > 0.0 (penuh >= 5.0)
    """
    return {
        "negatif": trapezoidal(macd_hist, -1e9, -1e9, -25.0, -5.0),
        "netral":  triangular(macd_hist, -10.0, 0.0, 10.0),
        "positif": trapezoidal(macd_hist, 0.0, 5.0, 1e9, 1e9),
    }


def fuzzify_bb_pctb(bb_pctb: float) -> dict:
    """
    Bollinger %B = (Close - BB_Lower) / (BB_Upper - BB_Lower).
    'rendah' penuh untuk %B <= 0.25 dan meluruh hingga 0.50 (paruh bawah pita Bollinger -> R2).
    'tinggi' penuh untuk %B >= 0.80 (harga dekat/menembus Upper Band).
    """
    return {
        "rendah": trapezoidal(bb_pctb, -1e9, -1e9, 0.25, 0.50),
        "sedang": triangular(bb_pctb, 0.30, 0.50, 0.70),
        "tinggi": trapezoidal(bb_pctb, 0.60, 0.80, 1e9, 1e9),
    }


def fuzzify_volume_ratio(vol_ratio: float) -> dict:
    """
    Volume Ratio = Volume hari ini / SMA(Volume, 20).
    'tinggi' mulai aktif saat volume di atas rata-rata 20 hari (> 1.0)
    dan penuh pada >= 1.35 (sesuai Tabel 1 R3: volume di atas rata-rata).
    """
    return {
        "rendah": trapezoidal(vol_ratio, 0, 0, 0.6, 0.9),
        "normal": triangular(vol_ratio, 0.7, 1.0, 1.3),
        "tinggi": trapezoidal(vol_ratio, 1.0, 1.35, 1e9, 1e9),
    }


def fuzzify_all(fuzzy_inputs: dict) -> dict:
    """Fuzzifikasi 4 input sekaligus dari dict fuzzy_inputs (output Christian)."""
    return {
        "rsi":    fuzzify_rsi(fuzzy_inputs["rsi_14"]),
        "macd":   fuzzify_macd_hist(fuzzy_inputs["macd_hist"]),
        "bb":     fuzzify_bb_pctb(fuzzy_inputs["bb_pct_b"]),
        "volume": fuzzify_volume_ratio(fuzzy_inputs["volume_ratio"]),
    }
