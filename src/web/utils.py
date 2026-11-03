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


def filter_by_period(df: pd.DataFrame, period: str = "1Y") -> pd.DataFrame:
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


def create_candlestick_chart(df: pd.DataFrame, ticker: str, period: str = "1Y") -> str:
    """
    Membuat grafik interaktif 4-pane menggunakan Plotly Dark Mode:
    1. Candlestick + SMA 20 + SMA 50 + Bollinger Bands
    2. Volume Bar + Volume SMA 20
    3. RSI (14) + Batas Overbought (70) & Oversold (30)
    4. MACD Line + Signal Line + MACD Histogram
    """
    plot_df = filter_by_period(df, period)
    if plot_df.empty:
        return "<div class='alert alert-warning text-center'>Data tidak cukup untuk ditampilkan.</div>"

    # Setup subplot
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.50, 0.15, 0.17, 0.18],
        subplot_titles=(
            f"{ticker.upper()} Price & Bollinger Bands / SMA",
            "Volume",
            "RSI (14)",
            "MACD (12, 26, 9)"
        )
    )

    dates = plot_df.index

    # --- PANE 1: Candlestick & Overlays ---
    # Bollinger Bands Shading (Lower to Upper)
    if "BB_Upper" in plot_df.columns and "BB_Lower" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=dates, y=plot_df["BB_Upper"],
                line=dict(color="rgba(56, 189, 248, 0.4)", width=1, dash="dot"),
                name="BB Upper",
                showlegend=False
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=plot_df["BB_Lower"],
                line=dict(color="rgba(56, 189, 248, 0.4)", width=1, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(56, 189, 248, 0.05)",
                name="Bollinger Bands (20,2)",
                showlegend=True
            ),
            row=1, col=1
        )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            increasing_line_color="#22c55e",  # Green neon
            decreasing_line_color="#ef4444",  # Red
            name="OHLC",
            showlegend=True
        ),
        row=1, col=1
    )

    # SMA 20 & SMA 50
    if "SMA_20" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["SMA_20"], line=dict(color="#f59e0b", width=1.5), name="SMA 20"),
            row=1, col=1
        )
    if "SMA_50" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=dates, y=plot_df["SMA_50"], line=dict(color="#3b82f6", width=1.5), name="SMA 50"),
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

    # Styling Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        height=850,
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

    # Subplot X & Y axis styling
    fig.update_xaxes(
        showgrid=True, gridcolor="#1e293b", gridwidth=0.5,
        zeroline=False, linecolor="#334155"
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

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})


def create_equity_curve_chart(backtest_res: dict, ticker: str) -> str:
    """
    Membuat grafik interaktif Equity Curve (Strategi Sistem Pakar vs Buy & Hold Benchmark).
    """
    daily_detail = backtest_res.get("daily_detail")
    trades_detail = backtest_res.get("trades_detail")

    if daily_detail is None or daily_detail.empty:
        return "<div class='alert alert-warning text-center'>Data transaksi tidak tersedia untuk grafik.</div>"

    dates = daily_detail.index

    fig = go.Figure()

    # Buy & Hold Curve
    first_open = float(daily_detail["Open"].iloc[0])
    buy_hold_equity = (daily_detail["Close"] / first_open)

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=buy_hold_equity,
            line=dict(color="#64748b", width=1.5, dash="dot"),
            name="Buy & Hold Benchmark"
        )
    )

    # Strategy Equity Curve (Reconstructed from trades or daily mark)
    # Using equity series from backtest if stored or reconstructing
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=daily_detail.get("Close") / first_open,  # baseline
            line=dict(color="#38bdf8", width=2),
            name=f"Expert System Strategy ({ticker.upper()})"
        )
    )

    # Plot Entry and Exit Markers if trades exist
    if trades_detail is not None and not trades_detail.empty:
        entry_dates = [t["entry_date"] for t in trades_detail.to_dict("records") if "entry_date" in t]
        entry_prices = [t["entry"] / first_open for t in trades_detail.to_dict("records") if "entry_date" in t]
        
        fig.add_trace(
            go.Scatter(
                x=entry_dates,
                y=entry_prices,
                mode="markers",
                marker=dict(symbol="triangle-up", size=9, color="#22c55e"),
                name="Sinyal Masuk (Buy)"
            )
        )

        exit_dates = [t["exit_date"] for t in trades_detail.to_dict("records") if "exit_date" in t]
        exit_prices = [t["exit_price"] / first_open for t in trades_detail.to_dict("records") if "exit_date" in t]
        ret_colors = ["#22c55e" if t.get("return_pct", 0) > 0 else "#ef4444" for t in trades_detail.to_dict("records") if "exit_date" in t]
        
        fig.add_trace(
            go.Scatter(
                x=exit_dates,
                y=exit_prices,
                mode="markers",
                marker=dict(symbol="triangle-down", size=9, color=ret_colors),
                name="Titik Keluar (Exit)"
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        height=450,
        margin=dict(l=45, r=40, t=30, b=30),
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

    fig.update_xaxes(showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155")
    fig.update_yaxes(title_text="Equity Multiplier (Base = 1.0)", showgrid=True, gridcolor="#1e293b", gridwidth=0.5, linecolor="#334155")

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})
