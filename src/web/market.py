"""
Status sesi perdagangan BEI/IDX (Waktu Indonesia Barat).

Dipakai oleh web app untuk menampilkan keadaan pasar saat ini
(PRA-PEMBUKAAN / SESI 1 / ISTIRAHAT / SESI 2 / TUTUP) dan kapan
event berikutnya terjadi.

Catatan: daftar hari libur bursa belum diambil otomatis dari IDX.
Tambahkan tanggalnya ke IDX_HOLIDAYS (format "YYYY-MM-DD") bila perlu.
"""

from datetime import date, datetime, time, timedelta

import pytz

WIB = pytz.timezone("Asia/Jakarta")

# Hari libur bursa (format "YYYY-MM-DD"). Kosong = hanya Sabtu/Minggu.
IDX_HOLIDAYS: set[str] = set()

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

# (mulai, selesai, kode, label) - jadwal reguler IDX, Senin-Kamis
WEEKDAY_WINDOWS = [
    (time(8, 45), time(8, 59, 59), "pre", "PRA-PEMBUKAAN"),
    (time(9, 0), time(11, 59, 59), "s1", "SESI 1"),
    (time(12, 0), time(13, 29, 59), "break", "ISTIRAHAT"),
    (time(13, 30), time(15, 49, 59), "s2", "SESI 2"),
    (time(15, 50), time(16, 14, 59), "post", "PASCA-PENUTUPAN"),
]

# Jumat: sesi 1 berakhir 11:30, sesi 2 mulai 14:00
FRIDAY_WINDOWS = [
    (time(8, 45), time(8, 59, 59), "pre", "PRA-PEMBUKAAN"),
    (time(9, 0), time(11, 29, 59), "s1", "SESI 1"),
    (time(11, 30), time(13, 59, 59), "break", "ISTIRAHAT"),
    (time(14, 0), time(15, 49, 59), "s2", "SESI 2"),
    (time(15, 50), time(16, 14, 59), "post", "PASCA-PENUTUPAN"),
]

EVENT_START_TEXT = {
    "pre": "Pra-pembukaan",
    "s1": "Sesi 1 dibuka",
    "break": "Istirahat",
    "s2": "Sesi 2 dibuka",
    "post": "Pasar tutup",
}

STATUS_COLOR = {
    "s1": "success",
    "s2": "success",
    "pre": "info",
    "post": "info",
    "break": "warning",
    "closed": "secondary",
    "weekend": "secondary",
    "holiday": "secondary",
}

OPEN_STATUSES = {"s1", "s2"}


def windows_for_weekday(weekday: int):
    """Daftar jendela sesi untuk hari ke-`weekday` (0=Senin)."""
    return FRIDAY_WINDOWS if weekday == 4 else WEEKDAY_WINDOWS


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day.isoformat() not in IDX_HOLIDAYS


def _at(day: date, moment: time) -> datetime:
    return WIB.localize(datetime.combine(day, moment))


def _next_event(now: datetime, windows):
    """Event bursa berikutnya setelah `now`."""
    candidates = [
        (_at(now.date(), start), f"{EVENT_START_TEXT.get(code, label)} {start:%H:%M}")
        for start, _end, code, label in windows
    ]
    candidates.sort(key=lambda item: item[0])
    for at, text in candidates:
        if at > now:
            return at, text

    # Sudah lewat sesi terakhir hari ini -> cari hari bursa berikutnya.
    probe = now.date()
    for _ in range(14):
        probe = probe + timedelta(days=1)
        if is_trading_day(probe):
            start = windows_for_weekday(probe.weekday())[0][0]
            return _at(probe, start), f"Pra-pembukaan {start:%H:%M}"
    return None, "Tidak ada jadwal"


def get_market_state(now: datetime | None = None) -> dict:
    """Snapshot keadaan pasar pada waktu `now` (default: sekarang, WIB)."""
    if now is None:
        now = datetime.now(WIB)
    elif now.tzinfo is None:
        now = WIB.localize(now)
    else:
        now = now.astimezone(WIB)

    trading = is_trading_day(now.date())
    windows = windows_for_weekday(now.weekday()) if trading else []

    status = "closed"
    label = "TUTUP"
    for start, end, code, window_label in windows:
        if start <= now.time() <= end:
            status, label = code, window_label
            break
    else:
        if now.weekday() >= 5:
            status, label = "weekend", "AKHIR PEKAN"
        elif not trading:
            status, label = "holiday", "LIBUR BURSA"

    next_at, next_text = _next_event(now, windows)
    seconds_until = max(0, int((next_at - now).total_seconds())) if next_at else None

    return {
        "status": status,
        "label": label,
        "color": STATUS_COLOR.get(status, "secondary"),
        "is_open": status in OPEN_STATUSES,
        "is_trading_day": trading,
        "day_name": DAY_NAMES[now.weekday()],
        "date": now.strftime("%Y-%m-%d"),
        "clock": now.strftime("%H:%M:%S"),
        "now_wib": now.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "now_ts": int(now.timestamp() * 1000),
        "next_event": {
            "at": next_at.strftime("%Y-%m-%d %H:%M") if next_at else None,
            "ts": int(next_at.timestamp() * 1000) if next_at else None,
            "label": next_text,
            "seconds": seconds_until,
        },
    }
