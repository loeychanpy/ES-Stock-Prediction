"""
Modul penjelasan: mengambil aturan yang terpicu dan membangun narasi
yang bisa ditampilkan di dashboard (fitur "Penjelasan Aturan" di laporan OUTPUT).
"""


FIRING_THRESHOLD = 0.1   # alpha minimum agar aturan dianggap "terpicu"


def filter_triggered(fired_rules: list) -> list:
    """Ambil aturan dengan alpha >= threshold, urut dari paling kuat."""
    triggered = [r for r in fired_rules if r["firing_strength"] >= FIRING_THRESHOLD]
    triggered.sort(key=lambda r: r["firing_strength"], reverse=True)
    return triggered


def build_explanation(signal_score: float, triggered: list, signal_valid: bool) -> str:
    """Narasi untuk ditampilkan di explanation panel."""
    if not signal_valid:
        return (
            "Sinyal tidak valid (filter Tahap 3 gagal). "
            "Aturan fuzzy tidak dievaluasi."
        )

    if not triggered:
        return (
            f"Tidak ada aturan R1-R4 yang terpicu signifikan. "
            f"Skor sinyal {signal_score:.2f}/100 - kondisi netral, rekomendasi TAHAN."
        )

    kuat = [r for r in triggered if r["consequent"] == "kuat"]
    sedang = [r for r in triggered if r["consequent"] == "sedang"]
    lemah = [r for r in triggered if r["consequent"] == "lemah"]

    parts = [f"Skor sinyal {signal_score:.2f}/100."]
    if kuat:
        parts.append(f"{len(kuat)} aturan 'kuat' terpicu.")
    if sedang:
        parts.append(f"{len(sedang)} aturan 'sedang' terpicu.")
    if lemah:
        parts.append(f"{len(lemah)} aturan 'lemah' aktif - menahan skor.")

    if signal_score >= 70:
        parts.append("Rekomendasi: BELI.")
    else:
        parts.append("Belum mencapai ambang 70 - rekomendasi TAHAN.")

    return " ".join(parts)
