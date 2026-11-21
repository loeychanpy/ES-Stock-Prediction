"""
Updater data pasar latar belakang (background thread).

Tugasnya: setiap `interval_seconds` (default 15 menit) pada sesi bursa,
mengunduh candle terbaru dari Yahoo Finance lewat modul Data Engineer,
lalu menulis ulang CSV/JSON di `storage_data/2_inference_ready`.

Dijalankan dari `run_web.py`, bukan dari `create_app()`, supaya import
aplikasi (mis. untuk unit test) tidak menyalakan thread.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from .market import WIB, get_market_state

try:  # pragma: no cover - import dijaga agar modul tetap bisa dipakai untuk test
    from data_indicators_engineers import export_all_stocks
except Exception:  # noqa: BLE001
    export_all_stocks = None


class MarketDataUpdater:
    """Thread daemon yang menjaga data candle tetap segar saat bursa buka."""

    def __init__(
        self,
        engine,
        tickers: list[str],
        export_fn=None,
        interval_seconds: int = 900,
        final_hour: int = 16,
        final_minute: int = 30,
        tickers_provider=None,
        logger=print,
    ):
        self.engine = engine
        self.tickers = list(tickers)
        self.export_fn = export_fn or export_all_stocks
        self.interval_seconds = max(60, int(interval_seconds))
        self.final_hour = final_hour
        self.final_minute = final_minute
        self.tickers_provider = tickers_provider
        self.logger = logger

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._force = False
        self._export_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._last_attempt: datetime | None = None
        self._final_done_for = None

        self._state = {
            "last_run_at": None,
            "last_run_kind": None,
            "last_duration_s": None,
            "last_error": None,
            "updated": [],
            "runs": 0,
        }

    # ---------------------------------------------------------------
    # API publik
    # ---------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="market-data-updater", daemon=True
        )
        self._thread.start()
        self.logger(
            f"[updater] aktif: cek tiap {self.interval_seconds // 60} menit "
            f"(sesi bursa 09:00-16:15 WIB, final EOD "
            f"{self.final_hour:02d}:{self.final_minute:02d} WIB)"
        )

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def request_refresh(self) -> None:
        """Minta update segera (dipakai tombol 'Perbarui' di web)."""
        self._force = True
        self._wake_event.set()

    def snapshot(self) -> dict:
        """Ringkasan status untuk endpoint /api/status dan template."""
        with self._state_lock:
            state = dict(self._state)
        state["running"] = bool(self._thread and self._thread.is_alive())
        state["interval_minutes"] = max(1, round(self.interval_seconds / 60))
        next_run = None
        if self._last_attempt is not None:
            next_run = self._last_attempt + timedelta(seconds=self.interval_seconds)
        state["next_run_at"] = next_run.strftime("%H:%M:%S WIB") if next_run else None
        state["next_run_ts"] = int(next_run.timestamp() * 1000) if next_run else None
        state["last_attempt_ts"] = (
            int(self._last_attempt.timestamp() * 1000) if self._last_attempt else None
        )
        return state

    # ---------------------------------------------------------------
    # Loop internal
    # ---------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001 - thread tidak boleh mati
                self._record_error(f"loop: {exc}")
            self._wake_event.wait(5)
            self._wake_event.clear()

    def _tick(self) -> None:
        now = datetime.now(WIB)
        market = get_market_state(now)
        after_close = (
            not market["is_trading_day"]
            or (now.hour, now.minute) >= (self.final_hour, self.final_minute)
        )

        force = self._force
        self._force = False

        # 1. Finalisasi EOD sekali per hari bursa (default 16:30 WIB).
        if market["is_trading_day"] and after_close:
            if self._final_done_for != now.date():
                self._run(now, is_final=True)
                self._final_done_for = now.date()
                return

        # 2. Update intraday tiap 15 menit selama sesi berjalan (atau saat dipaksa).
        if not market["is_open"] and not force:
            return

        due = (
            self._last_attempt is None
            or (now - self._last_attempt).total_seconds() >= self.interval_seconds
        )
        if force or due:
            # Setelah penutupan/akhir pekan, refresh manual tetap ditandai FINAL (EOD).
            self._run(now, is_final=after_close)

    def _run(self, now: datetime, is_final: bool) -> None:
        if self.export_fn is None:
            self._record_error("modul data_indicators_engineers tidak tersedia")
            return

        self._refresh_tickers()

        with self._export_lock:
            started = time.time()
            kind = "final" if is_final else "intraday"
            try:
                result = self.export_fn(self.engine, self.tickers, is_final=is_final)
                errors = (result or {}).get("failed") or {}
                updated = (result or {}).get("updated") or []
                duration = round(time.time() - started, 2)
                with self._state_lock:
                    self._state.update(
                        {
                            "last_run_at": now.strftime("%Y-%m-%d %H:%M:%S WIB"),
                            "last_run_kind": kind,
                            "last_duration_s": duration,
                            "last_error": (
                                "; ".join(f"{k}: {v}" for k, v in errors.items())
                                if errors
                                else None
                            ),
                            "updated": list(updated),
                            "runs": self._state["runs"] + 1,
                        }
                    )
                self._last_attempt = now
                self.logger(
                    f"[updater] {kind}: {', '.join(updated) if updated else 'tidak ada data'} "
                    f"({duration}s)"
                )
            except Exception as exc:  # noqa: BLE001
                self._last_attempt = now
                self._record_error(str(exc))

    def _refresh_tickers(self) -> None:
        """Ikutkan saham baru yang ditambahkan lewat web tanpa restart server."""
        if not self.tickers_provider:
            return
        try:
            available = self.tickers_provider()
        except Exception:  # noqa: BLE001
            return
        added = [t for t in available if t not in self.tickers]
        if added:
            self.tickers.extend(added)
            self.logger(f"[updater] saham baru ikut dipantau: {', '.join(added)}")

    def _record_error(self, message: str) -> None:
        with self._state_lock:
            self._state["last_error"] = message
        self.logger(f"[updater] ERROR: {message}")
