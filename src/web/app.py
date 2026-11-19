"""
Flask Web Application for Stock Trading Expert System (Kelompok 8)
Modul: Web App & Visualization (Krisantus)
"""

import os
import sys
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

# Ensure project paths are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)

for path in [ROOT_DIR, SRC_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from data_indicators_engineers import StockDataIndicatorEngineer
from rule_engine import infer, build_facts
from signal_validation_backtest import backtest, validate_signals
from .utils import (
    get_available_stocks,
    load_stock_df,
    load_stock_facts,
    create_candlestick_chart,
    create_equity_curve_chart,
    DATA_DIR,
    ROOT_DIR as APP_ROOT_DIR
)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(CURRENT_DIR, "templates"),
        static_folder=os.path.join(CURRENT_DIR, "static")
    )
    app.config["SECRET_KEY"] = "sistem-pakar-kelompok-8-secret-2026"
    engineer = StockDataIndicatorEngineer(base_dir=os.path.join(ROOT_DIR, "storage_data"))

    # ==========================================
    # ROUTE: DASHBOARD / ANALISIS SAHAM
    # ==========================================
    @app.route("/", methods=["GET", "POST"])
    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        available_stocks = get_available_stocks()

        if request.method == "POST":
            selected_ticker = request.form.get("ticker", "").upper().strip()
            period = request.form.get("period", "6M").upper().strip()
            n_days = int(request.form.get("n_days", 5))
            near_pct = float(request.form.get("near_pct", 3.0))
            tp_mult = float(request.form.get("tp_mult", 2.0))
            sl_mult = float(request.form.get("sl_mult", 1.0))
        else:
            selected_ticker = request.args.get("ticker", "").upper().strip()
            period = request.args.get("period", "6M").upper().strip()
            n_days = int(request.args.get("n_days", 5))
            near_pct = float(request.args.get("near_pct", 3.0))
            tp_mult = float(request.args.get("tp_mult", 2.0))
            sl_mult = float(request.args.get("sl_mult", 1.0))

        # Default ke saham pertama jika tidak dipilih
        if not selected_ticker:
            selected_ticker = available_stocks[0] if available_stocks else "BBCA"

        params = {
            "n_days": n_days,
            "near_pct": near_pct,
            "tp_mult": tp_mult,
            "sl_mult": sl_mult
        }

        # Cek apakah data saham lokal tersedia; jika belum ada, coba fetch otomatis
        df = load_stock_df(selected_ticker)
        facts = load_stock_facts(selected_ticker)

        if df.empty or not facts:
            try:
                res = engineer.process_and_export_files(selected_ticker, is_final=True)
                df = load_stock_df(selected_ticker)
                facts = res["facts"]
                if selected_ticker not in available_stocks:
                    available_stocks.append(selected_ticker)
                    available_stocks.sort()
            except Exception as e:
                flash(f"Gagal mengambil data untuk saham {selected_ticker}: {str(e)}", "danger")
                if available_stocks and selected_ticker != available_stocks[0]:
                    return redirect(url_for("dashboard", ticker=available_stocks[0], period=period))

        # Evaluasi inferensi Rule-Based & Pemindaian Riwayat Sinyal Terpicu (Track Record)
        inference_result = None
        history_signals = []
        signals_df = None

        if not df.empty:
            try:
                # Recalculate filter validasi NPMM sesuai parameter aktif (n_days & near_pct)
                val_df = validate_signals(df, n_days=n_days, near_pct=near_pct / 100.0)

                # Pindai seluruh riwayat untuk mendeteksi sinyal BELI yang pernah terpicu
                raw_signals_for_chart = []
                for pos in range(2, len(val_df)):
                    r = val_df.iloc[pos]
                    if pd.isna(r["ATR_14"]) or pd.isna(r["RSI_14"]):
                        continue
                    is_valid = bool(r["Signal_Valid_Recalc"])
                    cur_facts = build_facts(val_df, pos, is_valid, atr_tp_mult=tp_mult, atr_sl_mult=sl_mult)
                    res = infer(cur_facts)
                    if res["decision"] == "BELI":
                        dt_val = val_df.index[pos]
                        dt_str = dt_val.strftime("%Y-%m-%d")
                        rules_str = ", ".join(res["buy_rules_fired"])
                        prior_l = float(r["Prior_N_Day_Low"]) if pd.notna(r["Prior_N_Day_Low"]) else float(r["Low"])
                        dist_l = ((float(r["Close"]) - prior_l) / prior_l * 100.0) if prior_l > 0 else 0.0

                        history_signals.append({
                            "idx": len(history_signals) + 1,
                            "date": dt_val,
                            "date_str": dt_val.strftime("%d/%m/%Y"),
                            "date_iso": dt_str,
                            "close": float(r["Close"]),
                            "rules": rules_str,
                            "rules_list": res["buy_rules_fired"],
                            "rsi": round(float(r["RSI_14"]), 2),
                            "macd_h": round(float(r["MACD_Hist"]), 2),
                            "pctb": round(float(r["BB_PctB"]), 4),
                            "atr": round(float(r["ATR_14"]), 2),
                            "tp": round(float(cur_facts["risk_management"]["initial_tp_estimate"]), 2),
                            "sl": round(float(cur_facts["risk_management"]["initial_sl_estimate"]), 2),
                            "dist_pct": round(dist_l, 2),
                            "prior_low": round(prior_l, 2)
                        })
                        raw_signals_for_chart.append({
                            "signal_date": dt_str,
                            "entry_date": dt_str,
                            "entry": float(r["Close"]),
                            "buy_rules": rules_str,
                            "return_pct": 0.0,
                            "exit_date": None,
                            "exit_reason": ""
                        })

                if raw_signals_for_chart:
                    signals_df = pd.DataFrame(raw_signals_for_chart)

                # Evaluasi hari terakhir dengan parameter aktif
                last_pos = len(val_df) - 1
                last_valid = bool(val_df.iloc[-1]["Signal_Valid_Recalc"])
                facts = build_facts(val_df, last_pos, last_valid, atr_tp_mult=tp_mult, atr_sl_mult=sl_mult)
                facts["validation_filter"]["n_days"] = n_days
                facts["validation_filter"]["near_pct"] = near_pct
                facts["validation_filter"]["local_min_n"] = float(val_df.iloc[-1]["Prior_N_Day_Low"]) if pd.notna(val_df.iloc[-1]["Prior_N_Day_Low"]) else float(val_df.iloc[-1]["Low"])
                facts["validation_filter"]["local_min_valid"] = bool(val_df.iloc[-1]["Local_Min_Valid"])
                facts["validation_filter"]["trend_valid"] = bool(val_df.iloc[-1]["Trend_Valid"])
                facts["validation_filter"]["sma_20"] = float(val_df.iloc[-1]["SMA_20"])
                facts["validation_filter"]["sma_50"] = float(val_df.iloc[-1]["SMA_50"])
                facts["risk_management"]["atr_14"] = float(val_df.iloc[-1]["ATR_14"])
                facts["risk_management"]["tp_mult"] = tp_mult
                facts["risk_management"]["sl_mult"] = sl_mult
                inference_result = infer(facts)
            except Exception as e:
                flash(f"Gagal memproses inferensi rule-based: {str(e)}", "warning")

        # Buat grafik TradingView / Plotly Candlestick & Indikator (dengan Marker Riwayat Sinyal)
        chart_html = create_candlestick_chart(df, selected_ticker, period=period, signals_df=signals_df)

        # Ringkasan pergerakan harga
        df_info = {}
        if not df.empty:
            last_row = df.iloc[-1]
            prev_close = df.iloc[-2]["Close"] if len(df) > 1 else last_row["Close"]
            change = last_row["Close"] - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0.0

            df_info = {
                "latest_date": df.index[-1].strftime("%d %b %Y"),
                "latest_close": f"{last_row['Close']:,.0f}".replace(",", "."),
                "prev_close": f"{prev_close:,.0f}".replace(",", "."),
                "change": f"{change:+,.0f}".replace(",", "."),
                "change_pct": f"{change_pct:+.2f}%",
                "is_positive": change >= 0,
                "total_bars": len(df),
                "data_range": f"{df.index.min().strftime('%d/%m/%Y')} - {df.index.max().strftime('%d/%m/%Y')}"
            }

        return render_template(
            "dashboard.html",
            stocks=available_stocks,
            selected_ticker=selected_ticker,
            selected_period=period,
            params=params,
            chart_html=chart_html,
            inference=inference_result,
            facts=facts,
            df_info=df_info,
            history_signals=history_signals
        )

    # ==========================================
    # ROUTE: BACKTESTING & EVALUASI STRATEGI
    # ==========================================
    @app.route("/backtest", methods=["GET", "POST"])
    def backtesting():
        available_stocks = get_available_stocks()

        if request.method == "POST":
            ticker = request.form.get("ticker", available_stocks[0]).upper().strip()
            n_days = int(request.form.get("n_days", 5))
            near_pct = float(request.form.get("near_pct", 3.0)) / 100.0
            tp_mult = float(request.form.get("tp_mult", 2.0))
            sl_mult = float(request.form.get("sl_mult", 1.0))
        else:
            ticker = request.args.get("ticker", available_stocks[0]).upper().strip()
            n_days = int(request.args.get("n_days", 5))
            near_pct = float(request.args.get("near_pct", 3.0)) / 100.0
            tp_mult = float(request.args.get("tp_mult", 2.0))
            sl_mult = float(request.args.get("sl_mult", 1.0))

        df = load_stock_df(ticker)
        if df.empty:
            try:
                engineer.process_and_export_files(ticker, is_final=True)
                df = load_stock_df(ticker)
            except Exception as e:
                flash(f"Tidak dapat memuat data saham {ticker}: {str(e)}", "danger")
                return redirect(url_for("backtesting", ticker=available_stocks[0]))

        params = {
            "n_days": n_days,
            "near_pct": round(near_pct * 100, 1),
            "tp_mult": tp_mult,
            "sl_mult": sl_mult
        }

        # Jalankan modul simulasi backtest Felix
        backtest_result = None
        equity_chart_html = None
        trades_list = []

        try:
            backtest_result = backtest(
                df,
                n_days=n_days,
                near_pct=near_pct,
                atr_tp_mult=tp_mult,
                atr_sl_mult=sl_mult
            )
            equity_chart_html = create_equity_curve_chart(backtest_result, ticker)
            trades_df = backtest_result.get("trades_detail", None)
            if trades_df is not None and not trades_df.empty:
                trades_list = trades_df.to_dict(orient="records")
                # Format dates nicely
                for t in trades_list:
                    if hasattr(t.get("signal_date"), "strftime"):
                        t["signal_date_str"] = t["signal_date"].strftime("%d/%m/%Y")
                    else:
                        t["signal_date_str"] = str(t.get("signal_date", "-"))
                    if hasattr(t.get("entry_date"), "strftime"):
                        t["entry_date_str"] = t["entry_date"].strftime("%d/%m/%Y")
                    else:
                        t["entry_date_str"] = str(t.get("entry_date"))
                    if hasattr(t.get("exit_date"), "strftime"):
                        t["exit_date_str"] = t["exit_date"].strftime("%d/%m/%Y")
                    else:
                        t["exit_date_str"] = str(t.get("exit_date"))
        except Exception as e:
            flash(f"Terjadi kesalahan saat menjalankan backtesting: {str(e)}", "danger")

        return render_template(
            "backtest.html",
            stocks=available_stocks,
            selected_ticker=ticker,
            params=params,
            summary=backtest_result,
            equity_chart_html=equity_chart_html,
            trades=trades_list
        )

    # ==========================================
    # API: FETCH SAHAM BARU ATAU REFRESH
    # ==========================================
    @app.route("/api/fetch_stock", methods=["POST"])
    def fetch_stock():
        data = request.get_json(silent=True) or request.form
        ticker = data.get("ticker", "").upper().strip()
        if not ticker:
            return jsonify({"success": False, "error": "Kode saham wajib diisi"}), 400

        try:
            res = engineer.process_and_export_files(ticker, is_final=True)
            clean_code = res["ticker"]
            return jsonify({
                "success": True,
                "ticker": clean_code,
                "message": f"Data {clean_code} berhasil diperbarui!"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
