"""
Knowledge Base: aturan IF-THEN Pure Rule-Based (tanpa fuzzy, tanpa volume).

Semua aturan dipicu oleh KEJADIAN garis indikator yang disentuh / dilewati
(lihat indicator_events.py), bukan oleh rentang nilai.

Aturan BELI (pemicu naik):
  R1  RSI menyentuh 30 dari atas                                  -> BELI (sinyal terkuat)
  R2  MACD histogram merah -> hijau (lewat 0 ke atas) DAN RSI < 70 -> BELI
  R3  %B menyentuh garis 0 dari atas                              -> BELI (pantul naik)
  R4  %B menembus 0.5 ke atas DAN RSI < 70                        -> BELI (lanjut naik ke 1)
  R5  %B memantul naik di garis 0.5 DAN RSI < 70                  -> BELI

Aturan TAHAN (pemicu turun):
  R6  RSI menyentuh 70 dari bawah                                 -> TAHAN
  R7  MACD histogram hijau -> merah (lewat 0 ke bawah)            -> TAHAN
  R8  %B menyentuh garis 1 dari bawah                             -> TAHAN (berbalik turun)
  R9  %B menembus 0.5 ke bawah                                    -> TAHAN (lanjut turun ke 0)
  R10 %B ditolak di garis 0.5 (berbalik turun)                    -> TAHAN

Syarat "RSI < 70" pada R2/R4/R5 = RSI masih punya ruang naik menuju 70
(momentum buy), sesuai definisi RSI yang diminta.
"""

RULES = [
    # ------------------------- ATURAN BELI -------------------------
    {
        "id": "R1",
        "indicator": "RSI",
        "description": "IF RSI menyentuh 30 dari atas THEN BELI",
        "makna": "RSI turun menyentuh 30 (oversold): potensi harga berbalik naik, sinyal beli paling kuat.",
        "condition": lambda e: e["rsi"]["touch_30_from_above"],
        "consequent": "BELI",
    },
    {
        "id": "R2",
        "indicator": "MACD",
        "description": "IF histogram MACD merah berubah hijau (melewati garis 0 ke atas) AND RSI < 70 THEN BELI",
        "makna": "Terjadi pembalikan momentum dari turun ke naik, dan RSI masih punya ruang naik ke 70.",
        "condition": lambda e: e["macd"]["cross_up_zero"] and e["rsi"]["below_70"],
        "consequent": "BELI",
    },
    {
        "id": "R3",
        "indicator": "%B",
        "description": "IF %B menyentuh garis 0 dari atas THEN BELI",
        "makna": "%B menyentuh garis 0: indikasi harga memantul naik ke atas.",
        "condition": lambda e: e["bb"]["touch_0_from_above"],
        "consequent": "BELI",
    },
    {
        "id": "R4",
        "indicator": "%B",
        "description": "IF %B menembus garis 0.5 ke atas AND RSI < 70 THEN BELI",
        "makna": "Harga berhasil melewati garis tengah 0.5: berpotensi lanjut naik menuju garis 1.",
        "condition": lambda e: e["bb"]["cross_up_05"] and e["rsi"]["below_70"],
        "consequent": "BELI",
    },
    {
        "id": "R5",
        "indicator": "%B",
        "description": "IF %B memantul naik di garis 0.5 AND RSI < 70 THEN BELI",
        "makna": "%B turun menyentuh garis tengah 0.5 lalu berbalik naik (garis 0.5 menjadi pijakan).",
        "condition": lambda e: e["bb"]["bounce_up_05"] and e["rsi"]["below_70"],
        "consequent": "BELI",
    },
    # ------------------------- ATURAN TAHAN ------------------------
    {
        "id": "R6",
        "indicator": "RSI",
        "description": "IF RSI menyentuh 70 dari bawah THEN TAHAN",
        "makna": "RSI mencapai 70 (overbought): ruang naik habis, potensi turun.",
        "condition": lambda e: e["rsi"]["touch_70_from_below"],
        "consequent": "TAHAN",
    },
    {
        "id": "R7",
        "indicator": "MACD",
        "description": "IF histogram MACD hijau berubah merah (melewati garis 0 ke bawah) THEN TAHAN",
        "makna": "Terjadi pembalikan momentum dari naik ke turun: sinyal harga akan turun.",
        "condition": lambda e: e["macd"]["cross_down_zero"],
        "consequent": "TAHAN",
    },
    {
        "id": "R8",
        "indicator": "%B",
        "description": "IF %B menyentuh garis 1 dari bawah THEN TAHAN",
        "makna": "%B menyentuh garis 1: indikasi harga berbalik turun.",
        "condition": lambda e: e["bb"]["touch_1_from_below"],
        "consequent": "TAHAN",
    },
    {
        "id": "R9",
        "indicator": "%B",
        "description": "IF %B menembus garis 0.5 ke bawah THEN TAHAN",
        "makna": "Harga jatuh melewati garis tengah 0.5: berpotensi lanjut turun menuju garis 0.",
        "condition": lambda e: e["bb"]["cross_down_05"],
        "consequent": "TAHAN",
    },
    {
        "id": "R10",
        "indicator": "%B",
        "description": "IF %B ditolak di garis 0.5 (naik menyentuh lalu turun lagi) THEN TAHAN",
        "makna": "%B gagal menembus garis tengah 0.5 dan berbalik turun.",
        "condition": lambda e: e["bb"]["reject_down_05"],
        "consequent": "TAHAN",
    },
]

BUY_RULE_IDS = [r["id"] for r in RULES if r["consequent"] == "BELI"]
HOLD_RULE_IDS = [r["id"] for r in RULES if r["consequent"] == "TAHAN"]
ALL_RULE_IDS = [r["id"] for r in RULES]
