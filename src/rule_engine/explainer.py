"""Penyusun narasi penjelasan keputusan Rule-Based."""


def build_explanation(decision: str, buy_fired: list, hold_fired: list,
                      signal_valid: bool, has_previous: bool = True) -> str:
    if not signal_valid:
        return (
            "Filter Validasi Tahap 3 belum terpenuhi (tren belum naik SMA20 > SMA50 "
            "atau harga tidak dekat titik terendah 5 hari). Rekomendasi: TAHAN."
        )
    if not has_previous:
        return ("Data hari sebelumnya tidak tersedia, sehingga kejadian menyentuh/melewati "
                "garis indikator tidak dapat dideteksi. Rekomendasi: TAHAN.")

    if decision == "BELI":
        detail = "; ".join(f"{r['id']} ({r['makna']})" for r in buy_fired)
        return f"KEPUTUSAN BELI - pemicu aktif: {detail}"

    if buy_fired and hold_fired:
        buys = ", ".join(r["id"] for r in buy_fired)
        holds = "; ".join(f"{r['id']} ({r['makna']})" for r in hold_fired)
        return (f"KEPUTUSAN TAHAN - pemicu beli {buys} aktif, tetapi bertentangan dengan "
                f"pemicu turun: {holds}. Sistem memilih TAHAN (konservatif).")

    if hold_fired:
        holds = "; ".join(f"{r['id']} ({r['makna']})" for r in hold_fired)
        return f"KEPUTUSAN TAHAN - pemicu turun aktif: {holds}"

    return ("KEPUTUSAN TAHAN - hari ini tidak ada pemicu: RSI tidak menyentuh 30, histogram "
            "MACD tidak berubah merah->hijau, dan %B tidak menyentuh/menembus garis 0 atau 0.5.")
