"""
Utility functions for Web App:
- Chart creation with Plotly (Candlestick, Indicators, Equity Curve)
- Data loading and caching
- Integration helpers for Christian's scraper, Janisha's fuzzy engine, and Felix's backtester
"""

import os
import glob
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Setup paths
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "storage_data", "2_inference_ready")
OUT_DIR = os.path.join(ROOT_DIR, "storage_data", "4_backtesting")


def get_available_stocks() -> list[str]:
    """Mengambil daftar kode saham yang sudah memiliki file clean_indicators.csv."""
    files = glob.glob(os.path.join(DATA_DIR, "*_clean_indicators.csv"))
    stocks = sorted([os.path.basename(f).replace("_clean_indicators.csv", "") for f in files])
    return stocks if stocks else ["BBCA", "BBRI", "TLKM"]


def load_stock_df(code: str) -> pd.DataFrame:
    """Memuat DataFrame indikator dari CSV lokal."""
    code = code.upper().strip()
    path = os.path.join(DATA_DIR, f"{code}_clean_indicators.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, index_col="Date", parse_dates=True).sort_index()
    return df


def load_stock_facts(code: str) -> dict:
    """Memuat fakta hari terakhir dari file JSON."""
    code = code.upper().strip()
    path = os.path.join(DATA_DIR, f"{code}_latest_facts.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def filter_by_period(df: pd.DataFrame, period: str = "6M") -> pd.DataFrame:
    """Memfilter rentang waktu DataFrame (misal 3M, 6M, 1Y, 3Y, ALL)."""
    if df.empty:
        return df
    
    last_date = df.index.max()
    period = period.upper()
    if period == "3M":
        start_date = last_date - pd.DateOffset(months=3)
    elif period == "6M":
        start_date = last_date - pd.DateOffset(months=6)
    elif period == "1Y":
        start_date = last_date - pd.DateOffset(years=1)
    elif period == "3Y":
        start_date = last_date - pd.DateOffset(years=3)
    else:  # ALL
        return df
        
    filtered = df.loc[df.index >= start_date]
    return filtered if not filtered.empty else df


def create_candlestick_chart(df: pd.DataFrame, ticker: str, period: str = "6M") -> str:
    """
    Membuat grafik interaktif 5-pane menggunakan Plotly Dark Mode (sesuai OUTPUT butir 2):
    1. Candlestick (Solid Body) + SMA 20 + SMA 50 + Bollinger Bands
    2. Volume Bar + Volume SMA 20
    3. RSI (14) + Batas Overbought (70) & Oversold (30)
    4. MACD Line + Signal Line + MACD Histogram
    5. ATR (14) - Average True Range (Volatilitas Penentu TP & SL)
    """
    plot_df = filter_by_period(df, period)
    if plot_df.empty:
        return "<div class='alert alert-warning text-center'>Data tidak cukup untuk ditampilkan.</div>"

    # Setup subplot (5 panes)
    fig = make_subplots(
        rows=5,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.44, 0.13, 0.14, 0.15, 0.14],
        subplot_titles=(
            f"{ticker.upper()} Candlestick Price & Bollinger Bands / SMA",
            "Volume",
            "RSI (14)",
            "MACD (12, 26, 9)",
            "ATR (14) — Average True Range (Volatilitas)"
        )
    )

    dates = plot_df.index

    # --- PANE 1: Candlestick & Overlays ---
    # Bollinger Bands Shading (Lower to Upper)
    if "BB_Upper" in plot_df.columns and "BB_Lower" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=dates, y=plot_df["BB_Upper"],
                line=dict(color="rgba(56, 189, 248, 0.35)", width=1, dash="dot"),
                name="BB Upper",
                showlegend=False
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=plot_df["BB_Lower"],
                line=dict(color="rgba(56, 189, 248, 0.35)", width=1, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(56, 189, 248, 0.04)",
                name="Bollinger Bands (20,2)",
                showlegend=True
            ),
            row=1, col=1
        )

    # SMA 20 & SMA 50 (drawn behind candlesticks so candles stand out clearly)
    if "SMA_20" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["SMA_20"], line=dict(color="#f59e0b", width=1.4), name="SMA 20"),
            row=1, col=1
        )
    if "SMA_50" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["SMA_50"], line=dict(color="#3b82f6", width=1.4), name="SMA 50"),
            row=1, col=1
        )

    # Candlestick (Solid filled bodies so they look like proper candles, not thin lines)
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            increasing_line_color="#22c55e",
            increasing_fillcolor="#22c55e",
            decreasing_line_color="#ef4444",
            decreasing_fillcolor="#ef4444",
            whiskerwidth=0.4,
            name="Candlestick OHLC",
            showlegend=True
        ),
        row=1, col=1
    )

    # --- PANE 2: Volume Bar ---
    vol_colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(plot_df["Close"], plot_df["Open"])]
    fig.add_trace(
        go.Bar(x=dates, y=plot_df["Volume"], marker_color=vol_colors, name="Volume", showlegend=False),
        row=2, col=1
    )
    if "Volume_SMA_20" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["Volume_SMA_20"], line=dict(color="#a855f7", width=1.2), name="Vol SMA 20"),
            row=2, col=1
        )

    # --- PANE 3: RSI 14 ---
    if "RSI_14" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["RSI_14"], line=dict(color="#eab308", width=1.5), name="RSI 14"),
            row=3, col=1
        )
        # Thresholds 70 & 30
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=1, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", line_width=1, row=3, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(148, 163, 184, 0.05)", line_width=0, row=3, col=1)

    # --- PANE 4: MACD ---
    if "MACD_Line" in plot_df.columns and "MACD_Signal" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["MACD_Line"], line=dict(color="#38bdf8", width=1.5), name="MACD"),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["MACD_Signal"], line=dict(color="#fb923c", width=1.5), name="Signal"),
            row=4, col=1
        )
    if "MACD_Hist" in plot_df.columns:
        hist_colors = ["#22c55e" if h >= 0 else "#ef4444" for h in plot_df["MACD_Hist"]]
        fig.add_trace(
            go.Bar(x=dates, y=plot_df["MACD_Hist"], marker_color=hist_colors, name="MACD Hist", showlegend=False),
            row=4, col=1
        )
        fig.add_hline(y=0, line_color="#64748b", line_width=1, row=4, col=1)

    # --- PANE 5: ATR 14 ---
    if "ATR_14" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=plot_df["ATR_14"],
                line=dict(color="#f43f5e", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(244, 63, 94, 0.08)",
                name="ATR 14"
            ),
            row=5, col=1
        )

    # Styling Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        height=960,
        margin=dict(l=45, r=40, t=35, b=30),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color="#cbd5e1")
        ),
        font=dict(family="Inter, system-ui, sans-serif", color="#94a3b8")
    )

    # Hilangkan jeda akhir pekan (Sabtu-Minggu) agar batang candlestick lebar dan jelas
    fig.update_xaxes(
        showgrid=True, gridcolor="#1e293b", gridwidth=0.5,
        zeroline=False, linecolor="#334155",
        rangebreaks=[dict(bounds=["sat", "mon"])],
        rangeslider_visible=False
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#1e293b", gridwidth=0.5,
        zeroline=False, linecolor="#334155"
    )

    # Specialized Y-axis titles
    fig.update_yaxes(title_text="Harga (IDR)", row=1, col=1)
    fig.update_yaxes(title_text="Vol", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    fig.update_yaxes(title_text="MACD", row=4, col=1)
    fig.update_yaxes(title_text="ATR (IDR)", row=5, col=1)

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})


def create_equity_curve_chart(backtest_res: dict, ticker: str) -> str:
    """
    Membuat grafik interaktif 6-pane lengkap untuk halaman Backtest:
      - Pane 1: Candlestick Harga Saham (OHLC) + Bollinger Bands + SMA 20/50 + Titik Masuk (Buy) & Keluar (TP/SL)
      - Pane 2: Volume + Volume SMA 20
      - Pane 3: RSI (14) + Titik Sinyal BELI
      - Pane 4: MACD (12, 26, 9) + Histogram + Titik Sinyal BELI
      - Pane 5: ATR (14) — Volatilitas
      - Pane 6: Kurva Pertumbuhan Modal (Equity Curve Strategi vs Buy & Hold Benchmark)
    """
    daily_detail = backtest_res.get("daily_detail")
    trades_detail = backtest_res.get("trades_detail")

    if daily_detail is None or daily_detail.empty:
        return "<div class='alert alert-warning text-center'>Data transaksi tidak tersedia untuk grafik.</div>"

    dates = daily_detail.index
    first_open = float(daily_detail["Open"].iloc[0])

    fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.022,
        row_heights=[0.36, 0.11, 0.13, 0.13, 0.11, 0.16],
        subplot_titles=(
            f"Grafik Candlestick {ticker.upper()}, Bollinger Bands, SMA 20/50 & Titik Eksekusi (Entry / TP / SL)",
            "Volume & Volume SMA 20",
            "RSI (14) Saat Sinyal BELI",
            "MACD (12, 26, 9) & Histogram Saat Sinyal BELI",
            "ATR (14) — Average True Range (Volatilitas)",
            "Kurva Pertumbuhan Modal (Expert System Strategy vs Buy & Hold Benchmark)"
        )
    )

    # ==========================================================
    # PANE 1: CANDLESTICK HARGA SAHAM + BB + SMA + MARKER BUY/EXIT
    # ==========================================================
    if "BB_Upper" in daily_detail.columns and "BB_Lower" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(
                x=dates, y=daily_detail["BB_Upper"],
                line=dict(color="rgba(56, 189, 248, 0.35)", width=1, dash="dot"),
                name="BB Upper",
                showlegend=False
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=daily_detail["BB_Lower"],
                line=dict(color="rgba(56, 189, 248, 0.35)", width=1, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(56, 189, 248, 0.04)",
                name="Bollinger Bands (20,2)",
                showlegend=True
            ),
            row=1, col=1
        )

    if "SMA_20" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(
                x=dates, y=daily_detail["SMA_20"],
                line=dict(color="#f59e0b", width=1.3),
                name="SMA 20"
            ),
            row=1, col=1
        )
    if "SMA_50" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(
                x=dates, y=daily_detail["SMA_50"],
                line=dict(color="#3b82f6", width=1.3),
                name="SMA 50"
            ),
            row=1, col=1
        )

    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=daily_detail["Open"],
            high=daily_detail["High"],
            low=daily_detail["Low"],
            close=daily_detail["Close"],
            increasing_line_color="#22c55e",
            increasing_fillcolor="#22c55e",
            decreasing_line_color="#ef4444",
            decreasing_fillcolor="#ef4444",
            whiskerwidth=0.4,
            name=f"Candlestick {ticker.upper()}",
            showlegend=True
        ),
        row=1, col=1
    )

    # Plot Entry & Exit Markers on Pane 1 + Signal Markers on RSI (Pane 3) & MACD (Pane 4)
    if trades_detail is not None and not trades_detail.empty:
        records = trades_detail.to_dict("records")
        entry_dates, entry_prices, entry_texts = [], [], []
        exit_dates, exit_prices, exit_colors, exit_texts = [], [], [], []
        sig_dates, sig_rsi, sig_macd, sig_texts = [], [], [], []

        for idx_num, t in enumerate(records, start=1):
            sd = t.get("signal_date")
            if sd is not None and sd in daily_detail.index:
                s_row = daily_detail.loc[sd]
                sig_dates.append(sd)
                sig_rsi.append(float(s_row["RSI_14"]))
                sig_macd.append(float(s_row["MACD_Hist"]))
                sig_texts.append(
                    f"Trade #{idx_num} Sinyal BELI (Skor: {t.get('signal_strength', '-')}/100)<br>"
                    f"RSI: {s_row['RSI_14']:.2f} | MACD Hist: {s_row['MACD_Hist']:.2f} | %B: {s_row['BB_PctB']:.2f}"
                )

            ed = t.get("entry_date")
            if ed is not None:
                entry_dates.append(ed)
                entry_prices.append(float(t["entry"]))
                entry_texts.append(
                    f"Trade #{idx_num} — BELI (Open): Rp {t['entry']:,.0f}<br>"
                    f"Target TP: Rp {t['tp']:,.0f} | SL: Rp {t['sl']:,.0f}<br>"
                    f"Skor Sinyal Centroid: {t.get('signal_strength', '-')}/100"
                )

            xd = t.get("exit_date")
            if xd is not None:
                exit_dates.append(xd)
                exit_prices.append(float(t["exit_price"]))
                ret = t.get("return_pct", 0.0)
                exit_colors.append("#22c55e" if ret > 0 else "#facc15")
                exit_texts.append(
                    f"Trade #{idx_num} — KELUAR ({t.get('exit_reason', '-')}): Rp {t['exit_price']:,.0f}<br>"
                    f"Net Return: {ret:+.2f}%"
                )

        if entry_dates:
            fig.add_trace(
                go.Scatter(
                    x=entry_dates,
                    y=entry_prices,
                    mode="markers",
                    marker=dict(
                        symbol="triangle-up",
                        size=13,
                        color="#38bdf8",
                        line=dict(width=1.5, color="#ffffff")
                    ),
                    text=entry_texts,
                    hovertemplate="%{text}<extra>ENTRY BELI</extra>",
                    name="Titik Masuk (Buy)"
                ),
                row=1, col=1
            )

        if exit_dates:
            fig.add_trace(
                go.Scatter(
                    x=exit_dates,
                    y=exit_prices,
                    mode="markers",
                    marker=dict(
                        symbol="triangle-down",
                        size=13,
                        color=exit_colors,
                        line=dict(width=1.5, color="#0b0f19")
                    ),
                    text=exit_texts,
                    hovertemplate="%{text}<extra>EXIT (TP/SL)</extra>",
                    name="Titik Keluar (TP/SL)"
                ),
                row=1, col=1
            )

    # ==========================================================
    # PANE 2: VOLUME & VOLUME SMA 20
    # ==========================================================
    vol_colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(daily_detail["Close"], daily_detail["Open"])]
    fig.add_trace(
        go.Bar(x=dates, y=daily_detail["Volume"], marker_color=vol_colors, name="Volume", showlegend=False),
        row=2, col=1
    )
    if "Volume_SMA_20" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=daily_detail["Volume_SMA_20"], line=dict(color="#a855f7", width=1.2), name="Vol SMA 20"),
            row=2, col=1
        )

    # ==========================================================
    # PANE 3: RSI (14) + TITIK SINYAL BELI
    # ==========================================================
    if "RSI_14" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=daily_detail["RSI_14"], line=dict(color="#eab308", width=1.5), name="RSI 14"),
            row=3, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=1, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", line_width=1, row=3, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(148, 163, 184, 0.05)", line_width=0, row=3, col=1)
        if trades_detail is not None and not trades_detail.empty and sig_dates:
            fig.add_trace(
                go.Scatter(
                    x=sig_dates, y=sig_rsi, mode="markers",
                    marker=dict(symbol="circle", size=8, color="#38bdf8", line=dict(width=1, color="#ffffff")),
                    text=sig_texts, hovertemplate="%{text}<extra>SINYAL BELI</extra>",
                    name="Sinyal BELI pada RSI", showlegend=False
                ),
                row=3, col=1
            )

    # ==========================================================
    # PANE 4: MACD (12, 26, 9) & HISTOGRAM + TITIK SINYAL BELI
    # ==========================================================
    if "MACD_Line" in daily_detail.columns and "MACD_Signal" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=daily_detail["MACD_Line"], line=dict(color="#38bdf8", width=1.4), name="MACD"),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=daily_detail["MACD_Signal"], line=dict(color="#fb923c", width=1.4), name="Signal"),
            row=4, col=1
        )
    if "MACD_Hist" in daily_detail.columns:
        hist_colors = ["#22c55e" if h >= 0 else "#ef4444" for h in daily_detail["MACD_Hist"]]
        fig.add_trace(
            go.Bar(x=dates, y=daily_detail["MACD_Hist"], marker_color=hist_colors, name="MACD Hist", showlegend=False),
            row=4, col=1
        )
        fig.add_hline(y=0, line_color="#64748b", line_width=1, row=4, col=1)
        if trades_detail is not None and not trades_detail.empty and sig_dates:
            fig.add_trace(
                go.Scatter(
                    x=sig_dates, y=sig_macd, mode="markers",
                    marker=dict(symbol="circle", size=8, color="#38bdf8", line=dict(width=1, color="#ffffff")),
                    text=sig_texts, hovertemplate="%{text}<extra>SINYAL BELI</extra>",
                    name="Sinyal BELI pada MACD", showlegend=False
                ),
                row=4, col=1
            )

    # ==========================================================
    # PANE 5: ATR (14) — VOLATILITAS
    # ==========================================================
    if "ATR_14" in daily_detail.columns:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=daily_detail["ATR_14"],
                line=dict(color="#f43f5e", width=1.4),
                fill="tozeroy",
                fillcolor="rgba(244, 63, 94, 0.08)",
                name="ATR 14"
            ),
            row=5, col=1
        )

    # ==========================================================
    # PANE 6: EQUITY CURVE (STRATEGI VS BUY & HOLD BENCHMARK)
    # ==========================================================
    if "Buy_Hold_Equity" in daily_detail.columns:
        buy_hold_equity = daily_detail["Buy_Hold_Equity"]
    else:
        buy_hold_equity = (daily_detail["Close"] / first_open)

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=buy_hold_equity,
            line=dict(color="#64748b", width=1.5, dash="dot"),
            name="Buy & Hold Benchmark"
        ),
        row=6, col=1
    )

    if "Equity_Curve" in daily_detail.columns:
        strategy_equity = daily_detail["Equity_Curve"]
    else:
        strategy_equity = pd.Series(1.0, index=dates)

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=strategy_equity,
            line=dict(color="#38bdf8", width=2.2),
            name=f"Modal Strategi ({ticker.upper()})"
        ),
        row=6, col=1
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        height=1150,
        margin=dict(l=45, r=40, t=35, b=30),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.015,
            xanchor="left",
            x=0,
            font=dict(size=11, color="#cbd5e1")
        ),
        font=dict(family="Inter, system-ui, sans-serif", color="#94a3b8")
    )

    fig.update_xaxes(
        showgrid=True, gridcolor="#1e293b", gridwidth=0.5,
        linecolor="#334155",
        rangebreaks=[dict(bounds=["sat", "mon"])],
        rangeslider_visible=False
    )
    fig.update_yaxes(title_text="Harga (IDR)", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=1, col=1)
    fig.update_yaxes(title_text="Vol", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=3, col=1)
    fig.update_yaxes(title_text="MACD", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=4, col=1)
    fig.update_yaxes(title_text="ATR (IDR)", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=5, col=1)
    fig.update_yaxes(title_text="Modal (1.0)", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155", row=6, col=1)

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})
