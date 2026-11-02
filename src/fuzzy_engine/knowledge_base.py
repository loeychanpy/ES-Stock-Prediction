"""
Knowledge base: aturan fuzzy IF-THEN mengacu TABEL 1 LAPORAN KELOMPOK 8.

Operator: AND = min, OR = max (standar Mamdani).

Himpunan output "kekuatan sinyal beli": {lemah, sedang, kuat}

Hanya ada 4 aturan sesuai Tabel 1 laporan.
"""


RULES = [
    {
        "id": "R1",
        "description": "IF RSI rendah AND histogram MACD positif THEN kekuatan sinyal beli kuat",
        "makna": "Menggabungkan kondisi jenuh jual dari RSI dengan momentum naik "
                 "dari MACD sebagai indikasi awal pembalikan.",
        "antecedent": lambda f: min(f["rsi"]["rendah"], f["macd"]["positif"]),
        "consequent": "kuat",
    },
    {
        "id": "R2",
        "description": "IF RSI rendah AND %B rendah THEN kekuatan sinyal beli sedang",
        "makna": "Harga berada dekat pita bawah Bollinger saat jenuh jual, "
                 "tetapi konfirmasi momentum belum ada.",
        "antecedent": lambda f: min(f["rsi"]["rendah"], f["bb"]["rendah"]),
        "consequent": "sedang",
    },
    {
        "id": "R3",
        "description": "IF histogram MACD positif AND rasio volume tinggi THEN kekuatan sinyal beli sedang",
        "makna": "Momentum naik yang didukung volume di atas rata-rata.",
        "antecedent": lambda f: min(f["macd"]["positif"], f["volume"]["tinggi"]),
        "consequent": "sedang",
    },
    {
        "id": "R4",
        "description": "IF RSI tinggi OR histogram MACD negatif THEN kekuatan sinyal beli lemah",
        "makna": "Momentum tidak mendukung pembelian sehingga rekomendasi "
                 "cenderung TAHAN.",
        "antecedent": lambda f: max(f["rsi"]["tinggi"], f["macd"]["negatif"]),
        "consequent": "lemah",
    },
]
