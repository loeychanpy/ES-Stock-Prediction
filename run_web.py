"""
Runner script for Stock Trading Expert System Web Application.
Kelompok 8 - UKRIDA (Krisantus)

Usage:
    python run_web.py
    python run_web.py --port 5000
"""

import os
import sys
import argparse

# Log updater langsung terlihat walau stdout dialihkan ke file.
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.web.app import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stock Expert System Web App")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
    parser.add_argument("--no-auto-update", action="store_true",
                        help="Disable background 15-minute data updater")
    parser.add_argument("--interval", type=int, default=15,
                        help="Auto-update interval in minutes (default: 15)")
    args = parser.parse_args()

    app = create_app()

    # ------------------------------------------------------------
    # Background updater: candle dari yfinance tiap 15 menit
    # ------------------------------------------------------------
    updater = None
    if not args.no_auto_update:
        is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        if args.no_debug or is_reloader_child:
            from src.web.updater import MarketDataUpdater
            from src.web.utils import get_available_stocks

            updater = MarketDataUpdater(
                engine=app.extensions["engine"],
                tickers=get_available_stocks(),
                interval_seconds=max(60, args.interval * 60),
                tickers_provider=get_available_stocks,
            )
            updater.start()
            app.extensions["market_updater"] = updater
        # Proses induk (reloader) tidak menjalankan updater agar tidak dobel.
    print("\n" + "=" * 60)
    print(" STOCK TRADING EXPERT SYSTEM (BEI/IDX)")
    print(" Kelompok 8 - UKRIDA 2026")
    print(" Modul: Web App & Visualization (Krisantus)")
    print(f" Akses Website di: http://{args.host}:{args.port}")
    if args.no_auto_update:
        print(" Auto-update: NONAKTIF (--no-auto-update)")
    else:
        print(f" Auto-update: aktif tiap {args.interval} menit pada sesi bursa")
        print("               Final EOD 16:30 WIB, tombol 'Perbarui' untuk manual")
    print(" Tekan CTRL+C untuk menghentikan server.")
    print("=" * 60 + "\n")

    app.run(host=args.host, port=args.port, debug=not args.no_debug)
