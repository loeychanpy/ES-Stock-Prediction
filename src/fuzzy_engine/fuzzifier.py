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
      - 'rendah' penuh (membership=1) untuk RSI <= 30  [sesuai laporan ref 3]
      - 'tinggi' penuh (membership=1) untuk RSI >= 70  [overbought]
    """
    return {
        "rendah": trapezoidal(rsi, 0, 0, 30, 45),
        "sedang": triangular(rsi, 30, 50, 70),
        "tinggi": trapezoidal(rsi, 55, 70, 100, 100),
    }


def fuzzify_macd_hist(macd_hist: float) -> dict:
    """
    MACD Histogram = MACD_Line - MACD_Signal.
    Positif = momentum naik (golden cross); negatif = momentum turun.
    Catatan: ambang 0.5 adalah nilai awal — dikalibrasi di tahap pengujian
    karena skala MACD bergantung harga saham.
    """
    return {
        "negatif": trapezoidal(macd_hist, -1e9, -1e9, -0.5, 0.0),
        "netral":  triangular(macd_hist, -0.5, 0.0, 0.5),
        "positif": trapezoidal(macd_hist, 0.0, 0.5, 1e9, 1e9),
    }


def fuzzify_bb_pctb(bb_pctb: float) -> dict:
    """
    Bollinger %B = (Close - BB_Lower) / (BB_Upper - BB_Lower).
    'rendah' penuh untuk %B <= 0.2 (harga dekat/menembus Lower Band -> R2).
    'tinggi' penuh untuk %B >= 0.8 (harga dekat/menembus Upper Band).
    """
    return {
        "rendah": trapezoidal(bb_pctb, -1e9, -1e9, 0.2, 0.4),
        "sedang": triangular(bb_pctb, 0.3, 0.5, 0.7),
        "tinggi": trapezoidal(bb_pctb, 0.6, 0.8, 1e9, 1e9),
    }


def fuzzify_volume_ratio(vol_ratio: float) -> dict:
    """
    Volume Ratio = Volume hari ini / SMA(Volume, 20).
    'tinggi' penuh untuk ratio >= 1.5 (volume spike -> konfirmasi minat beli, R3).
    """
    return {
        "rendah": trapezoidal(vol_ratio, 0, 0, 0.6, 0.9),
        "normal": triangular(vol_ratio, 0.7, 1.0, 1.3),
        "tinggi": trapezoidal(vol_ratio, 1.2, 1.5, 1e9, 1e9),
    }


def fuzzify_all(fuzzy_inputs: dict) -> dict:
    """Fuzzifikasi 4 input sekaligus dari dict fuzzy_inputs (output Christian)."""
    return {
        "rsi":    fuzzify_rsi(fuzzy_inputs["rsi_14"]),
        "macd":   fuzzify_macd_hist(fuzzy_inputs["macd_hist"]),
        "bb":     fuzzify_bb_pctb(fuzzy_inputs["bb_pct_b"]),
        "volume": fuzzify_volume_ratio(fuzzy_inputs["volume_ratio"]),
    }
