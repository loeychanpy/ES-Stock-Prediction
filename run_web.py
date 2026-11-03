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
    args = parser.parse_args()

    app = create_app()
    print("\n" + "=" * 60)
    print(" STOCK TRADING EXPERT SYSTEM (BEI/IDX)")
    print(" Kelompok 8 - UKRIDA 2026")
    print(" Modul: Web App & Visualization (Krisantus)")
    print(f" Akses Website di: http://{args.host}:{args.port}")
    print(" Tekan CTRL+C untuk menghentikan server.")
    print("=" * 60 + "\n")

    app.run(host=args.host, port=args.port, debug=not args.no_debug)
