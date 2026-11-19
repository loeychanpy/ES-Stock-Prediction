"""
TradingView Superchart Component Generator
Kelompok 8 - UKRIDA (Krisantus)

Menghasilkan antarmuka grafik interaktif yang identik dengan TradingView Supercharts:
- Engine: TradingView Lightweight Charts (v4)
- Dukungan Multi-Timeframe Candle Sebenarnya (Candle Resolution):
  * 1D (Daily)  : 1 Lilin melambangkan 1 Hari bursa
  * 1W (Weekly) : 1 Lilin melambangkan 1 Minggu bursa (Open awal minggu, High/Low seminggu, Close akhir minggu)
  * 1M (Monthly): 1 Lilin melambangkan 1 Bulan bursa (Open awal bulan, High/Low sebulan, Close akhir bulan)
  * Indikator pada timeframe 1W/1M dihitung ulang dari OHLC hasil agregasi,
    sedangkan timeframe 1D memakai nilai indikator resmi dari modul Data Engineer!
- Rentang Tampilan (Zoom Waktu) Terpisah:
  * 1 Bulan, 3 Bulan, 6 Bulan, 1 Tahun, Semua Data
- 5/6 Pane Tersinkronisasi:
  1. Candlestick OHLC + SMA 20 + SMA 50 + Marker Buy / Exit
  2. Indikator %B (Garis Acuan 0.0, 0.5, 1.0)
  3. RSI (14) (Garis 30 & 70)
  4. MACD (Line, Signal, Histogram warna Hijau/Merah)
  5. ATR (14) Volatilitas
  6. (Backtest) Kurva Pertumbuhan Modal (Equity Curve Strategi vs Buy & Hold)
- Kontrol & Interaksi Sesuai TradingView Superchart:
  * Scroll pada chart: Zoom horizontal (sumbu waktu / bars)
  * Drag pada chart: Panning geser riwayat waktu ke kiri/kanan
  * Scroll / Drag pada sumbu harga kanan: Stretch & Compress skala harga vertikal
  * Double-click pada sumbu harga: Auto-fit reset skala vertikal
  * Garis Vertikal Crosshair Tersinkronisasi: Menembus seluruh pane secara bersamaan
  * Legend real-time reaktif untuk setiap bar pada semua pane
  * Toolbar Alat TradingView: Crosshair, Penggaris (Ruler), Garis Horizontal Support/Resistance, Reset Zoom
"""

import json
import pandas as pd
import numpy as np


def _clean(val, decimals=4):
    if val is None or pd.isna(val) or not np.isfinite(val):
        return None
    return round(float(val), decimals)


def _compute_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Menghitung indikator teknikal (%B, RSI, MACD, SMA 20/50, ATR) pada DataFrame.

    Untuk timeframe harian, DataFrame dari modul indikator sudah memiliki kolom
    indikator resmi, sehingga dipakai apa adanya agar nilainya identik dengan
    fakta yang dipakai mesin inferensi. Timeframe 1W/1M dihitung ulang dari OHLC.
    """
    d = data.copy()
    if len(d) == 0:
        return d
    if {"BB_PctB", "RSI_14", "ATR_14"}.issubset(d.columns):
        return d

    # 1. SMA 20 & 50 (min_periods penuh agar tidak muncul SMA 50 semu pada timeframe 1M)
    d["SMA_20"] = d["Close"].rolling(20, min_periods=20).mean()
    d["SMA_50"] = d["Close"].rolling(50, min_periods=50).mean()

    # 2. RSI 14 (Wilder's smoothing, sama dengan modul indikator)
    delta = d["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    d["RSI_14"] = 100 - (100 / (1 + rs))

    # 3. MACD (12, 26, 9)
    ema_12 = d["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = d["Close"].ewm(span=26, adjust=False).mean()
    d["MACD_Line"] = ema_12 - ema_26
    d["MACD_Signal"] = d["MACD_Line"].ewm(span=9, adjust=False).mean()
    d["MACD_Hist"] = d["MACD_Line"] - d["MACD_Signal"]

    # 4. Bollinger Bands (20, 2) & %B
    bb_std = d["Close"].rolling(20, min_periods=20).std()
    d["BB_Middle"] = d["SMA_20"]
    d["BB_Upper"] = d["BB_Middle"] + (2 * bb_std)
    d["BB_Lower"] = d["BB_Middle"] - (2 * bb_std)
    bb_range = (d["BB_Upper"] - d["BB_Lower"]).replace(0, np.nan)
    d["BB_PctB"] = (d["Close"] - d["BB_Lower"]) / bb_range

    # 5. ATR (14) - Average True Range
    hl = d["High"] - d["Low"]
    hc = (d["High"] - d["Close"].shift(1)).abs()
    lc = (d["Low"] - d["Close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    d["ATR_14"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    return d


def _build_timeframe_data(sub_df: pd.DataFrame, trades_df: pd.DataFrame = None) -> dict:
    """Mengonversi DataFrame satu timeframe menjadi struktur data siap pakai Lightweight Charts."""
    sub_sorted = sub_df.sort_index()
    dates = [d.strftime("%Y-%m-%d") for d in sub_sorted.index]

    candles = []
    sma20, sma50 = [], []
    pctb = []
    rsi14 = []
    macd_l, macd_s, macd_h = [], [], []
    atr14 = []
    equity_strat, equity_bh = [], []

    for dt_str, (_, row) in zip(dates, sub_sorted.iterrows()):
        o = _clean(row.get("Open"), 2)
        h = _clean(row.get("High"), 2)
        l = _clean(row.get("Low"), 2)
        c = _clean(row.get("Close"), 2)
        if None in (o, h, l, c):
            continue

        candles.append({"time": dt_str, "open": o, "high": h, "low": l, "close": c})

        s20 = _clean(row.get("SMA_20"), 2)
        if s20 is not None:
            sma20.append({"time": dt_str, "value": s20})

        s50 = _clean(row.get("SMA_50"), 2)
        if s50 is not None:
            sma50.append({"time": dt_str, "value": s50})

        b = _clean(row.get("BB_PctB"), 4)
        if b is not None:
            pctb.append({"time": dt_str, "value": b})

        r = _clean(row.get("RSI_14"), 2)
        if r is not None:
            rsi14.append({"time": dt_str, "value": r})

        ml = _clean(row.get("MACD_Line"), 3)
        if ml is not None:
            macd_l.append({"time": dt_str, "value": ml})

        ms = _clean(row.get("MACD_Signal"), 3)
        if ms is not None:
            macd_s.append({"time": dt_str, "value": ms})

        mh = _clean(row.get("MACD_Hist"), 3)
        if mh is not None:
            macd_h.append({
                "time": dt_str,
                "value": mh,
                "color": "#089981" if mh >= 0 else "#f23645"
            })

        a = _clean(row.get("ATR_14"), 2)
        if a is not None:
            atr14.append({"time": dt_str, "value": a})

        if "Equity_Curve" in row and pd.notna(row["Equity_Curve"]):
            equity_strat.append({"time": dt_str, "value": _clean(row["Equity_Curve"], 4)})
        if "Buy_Hold_Equity" in row and pd.notna(row["Buy_Hold_Equity"]):
            equity_bh.append({"time": dt_str, "value": _clean(row["Buy_Hold_Equity"], 4)})

    # Marker titik transaksi
    entry_markers = []
    indicator_markers = []
    if trades_df is not None and not trades_df.empty and len(sub_sorted.index) > 0:
        raw_markers = []
        raw_ind_markers = []
        sub_idx = sub_sorted.index

        for idx, t in enumerate(trades_df.to_dict("records"), start=1):
            s_date = t.get("signal_date")
            e_date = t.get("entry_date")
            x_date = t.get("exit_date")

            rule_txt = t.get("buy_rules", "")
            ret = float(t.get("return_pct", 0.0))
            reason = t.get("exit_reason", "")

            # Cari bar terdekat di timeframe ini
            if e_date is not None:
                p_date = pd.Timestamp(e_date)
                pos = sub_idx.searchsorted(p_date)
                if pos < len(sub_idx):
                    bar_time = sub_idx[pos].strftime("%Y-%m-%d")
                    raw_markers.append({
                        "time": bar_time,
                        "position": "belowBar",
                        "color": "#089981",
                        "shape": "arrowUp",
                        "text": f"BUY #{idx} Rp {t.get('entry', 0):,.0f} ({rule_txt})"
                    })

            if x_date is not None:
                p_date = pd.Timestamp(x_date)
                pos = sub_idx.searchsorted(p_date)
                if pos < len(sub_idx):
                    bar_time = sub_idx[pos].strftime("%Y-%m-%d")
                    raw_markers.append({
                        "time": bar_time,
                        "position": "aboveBar",
                        "color": "#089981" if ret > 0 else "#f23645",
                        "shape": "arrowDown",
                        "text": f"EXIT #{idx} ({reason}) {ret:+.2f}%"
                    })

            if s_date is not None:
                p_date = pd.Timestamp(s_date)
                pos = sub_idx.searchsorted(p_date)
                if pos < len(sub_idx):
                    bar_time = sub_idx[pos].strftime("%Y-%m-%d")
                    raw_ind_markers.append({
                        "time": bar_time,
                        "position": "inBar",
                        "color": "#38bdf8",
                        "shape": "circle",
                        "text": f"Sinyal #{idx} ({rule_txt})"
                    })

        raw_markers.sort(key=lambda m: m["time"])
        raw_ind_markers.sort(key=lambda m: m["time"])
        entry_markers = raw_markers
        indicator_markers = raw_ind_markers

    return {
        "candles": candles,
        "sma20": sma20,
        "sma50": sma50,
        "pctb": pctb,
        "rsi14": rsi14,
        "macd_line": macd_l,
        "macd_signal": macd_s,
        "macd_hist": macd_h,
        "atr14": atr14,
        "equity_strat": equity_strat,
        "equity_bh": equity_bh,
        "entry_markers": entry_markers,
        "indicator_markers": indicator_markers,
        "total_bars": len(candles)
    }


def prepare_chart_data(df: pd.DataFrame, trades_df: pd.DataFrame = None) -> dict:
    """
    Menyiapkan data multi-timeframe (1D, 1W, 1M) lengkap:
    - 1D: 1 Lilin = 1 Hari bursa (Daily)
    - 1W: 1 Lilin = 1 Minggu bursa (Weekly)
    - 1M: 1 Lilin = 1 Bulan bursa (Monthly)
    """
    df_sorted = df.sort_index()

    # 1. Timeframe 1D (Harian)
    df_1d = _compute_indicators(df_sorted)
    data_1d = _build_timeframe_data(df_1d, trades_df=trades_df)

    # 2. Timeframe 1W (Mingguan)
    agg_dict = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }
    if "Equity_Curve" in df_sorted.columns:
        agg_dict["Equity_Curve"] = "last"
    if "Buy_Hold_Equity" in df_sorted.columns:
        agg_dict["Buy_Hold_Equity"] = "last"

    df_1w = df_sorted.resample("W-FRI").agg(agg_dict).dropna(subset=["Open", "Close"])
    df_1w = _compute_indicators(df_1w)
    data_1w = _build_timeframe_data(df_1w, trades_df=trades_df)

    # 3. Timeframe 1M (Bulanan)
    try:
        df_1m = df_sorted.resample("ME").agg(agg_dict).dropna(subset=["Open", "Close"])
    except Exception:
        df_1m = df_sorted.resample("M").agg(agg_dict).dropna(subset=["Open", "Close"])
    df_1m = _compute_indicators(df_1m)
    data_1m = _build_timeframe_data(df_1m, trades_df=trades_df)

    return {
        "timeframes": {
            "1D": data_1d,
            "1W": data_1w,
            "1M": data_1m
        },
        "currentTimeframe": "1D",
        "meta": {
            "1D": {"label": "1D", "desc": "1 Lilin = 1 Hari (Daily)", "count": len(data_1d["candles"])},
            "1W": {"label": "1W", "desc": "1 Lilin = 1 Minggu (Weekly)", "count": len(data_1w["candles"])},
            "1M": {"label": "1M", "desc": "1 Lilin = 1 Bulan (Monthly)", "count": len(data_1m["candles"])},
        }
    }


def render_tradingview_superchart(df: pd.DataFrame, ticker: str,
                                  chart_id: str = "tv_dashboard",
                                  trades_df: pd.DataFrame = None,
                                  is_backtest: bool = False,
                                  plotly_fallback_html: str = "") -> str:
    """
    Menghasilkan HTML + JavaScript lengkap komponen TradingView Superchart.
    """
    multi_data = prepare_chart_data(df, trades_df=trades_df)
    data_json = json.dumps(multi_data)
    is_backtest_js = "true" if is_backtest else "false"
    ticker_clean = ticker.upper()

    html = f"""
<div class="tv-superchart-wrapper" id="{chart_id}_wrapper">
  <!-- Top TradingView Header Bar -->
  <div class="tv-top-toolbar d-flex align-items-center justify-content-between flex-wrap gap-2">
    <!-- Left: Ticker, Timeframe Candle Selector & Live OHLC -->
    <div class="d-flex align-items-center gap-2 flex-wrap">
      <!-- Symbol Badge -->
      <div class="tv-symbol-pill">
        <span class="tv-symbol-text">{ticker_clean}</span>
        <span class="tv-exchange-badge">IDX</span>
        <span class="tv-interval-badge" id="{chart_id}_interval_badge">1D</span>
      </div>

      <!-- Timeframe Candle Selector (1 Lilin = Berapa Lama) -->
      <div class="d-flex align-items-center gap-1 ms-1">
        <span class="tv-selector-label text-muted d-none d-sm-inline">TIMEFRAME CANDLE:</span>
        <div class="btn-group btn-group-sm" role="group" aria-label="Candle Timeframe">
          <button type="button" class="btn tv-tf-btn active" id="{chart_id}_tf_1D" onclick="{chart_id}_setTimeframe('1D')" title="1 Lilin melambangkan transaksi 1 Hari (Daily)">
            1D
          </button>
          <button type="button" class="btn tv-tf-btn" id="{chart_id}_tf_1W" onclick="{chart_id}_setTimeframe('1W')" title="1 Lilin melambangkan transaksi 1 Minggu (Weekly)">
            1W
          </button>
          <button type="button" class="btn tv-tf-btn" id="{chart_id}_tf_1M" onclick="{chart_id}_setTimeframe('1M')" title="1 Lilin melambangkan transaksi 1 Bulan (Monthly)">
            1M
          </button>
        </div>
        <span class="badge tv-tf-desc-pill d-none d-md-inline ms-1" id="{chart_id}_tf_info">
          <i class="bi bi-calendar-day me-1 text-info"></i>1 Lilin = 1 Hari (Daily)
        </span>
      </div>

      <!-- Live OHLC Banner -->
      <div class="tv-ohlc-banner font-mono-num ms-2" id="{chart_id}_ohlc_banner">
        <span class="tv-label">O</span> <span id="{chart_id}_o" class="tv-val">-</span>
        <span class="tv-label ms-2">H</span> <span id="{chart_id}_h" class="tv-val">-</span>
        <span class="tv-label ms-2">L</span> <span id="{chart_id}_l" class="tv-val">-</span>
        <span class="tv-label ms-2">C</span> <span id="{chart_id}_c" class="tv-val">-</span>
        <span id="{chart_id}_chg" class="ms-2 tv-chg">-</span>
      </div>
    </div>

    <!-- Right: View Controls & Toggle Mode -->
    <div class="d-flex align-items-center gap-1">
      <button type="button" class="btn tv-icon-btn" onclick="{chart_id}_resetView()" title="Auto-Fit / Reset Skala Tampilan">
        <i class="bi bi-arrow-counterclockwise me-1"></i><span class="d-none d-md-inline">Auto-Fit</span>
      </button>
      <button type="button" class="btn tv-icon-btn" onclick="{chart_id}_toggleFullscreen()" title="Layar Penuh (Fullscreen)">
        <i class="bi bi-arrows-fullscreen"></i>
      </button>
      
      <!-- Toggle Mode View (TradingView vs Plotly) -->
      <div class="btn-group btn-group-sm ms-2">
        <button type="button" id="{chart_id}_btn_tv" class="btn btn-outline-info active btn-sm" onclick="{chart_id}_switchMode('tv')" style="font-size: 0.72rem;">
          <i class="bi bi-activity me-1"></i>TradingView
        </button>
        <button type="button" id="{chart_id}_btn_plotly" class="btn btn-outline-secondary btn-sm" onclick="{chart_id}_switchMode('plotly')" style="font-size: 0.72rem;">
          <i class="bi bi-bar-chart-steps me-1"></i>Plotly
        </button>
      </div>
    </div>
  </div>

  <!-- TradingView Superchart View Container -->
  <div id="{chart_id}_tv_view" class="tv-view-container position-relative">
    <div class="d-flex w-100">
      <!-- Left TradingView Toolbar Tools -->
      <div class="tv-left-toolbar d-flex flex-column align-items-center">
        <button type="button" class="tv-tool-btn active" id="{chart_id}_tool_crosshair" onclick="{chart_id}_setTool('crosshair')" title="Kursor Crosshair Tersinkronisasi">
          <i class="bi bi-crosshair"></i>
        </button>
        <button type="button" class="tv-tool-btn" id="{chart_id}_tool_ruler" onclick="{chart_id}_setTool('ruler')" title="Penggaris / Ruler (Ukur Rentang Bar &amp; % Untung/Rugi)">
          <i class="bi bi-rulers"></i>
        </button>
        <button type="button" class="tv-tool-btn" id="{chart_id}_tool_hline" onclick="{chart_id}_setTool('hline')" title="Garis Acuan Horizontal (Support / Resistance)">
          <i class="bi bi-dash-lg"></i>
        </button>
        <div class="tv-tool-sep"></div>
        <button type="button" class="tv-tool-btn" onclick="{chart_id}_clearDrawings()" title="Hapus Gambar Penggaris / Garis Acuan">
          <i class="bi bi-trash3"></i>
        </button>
      </div>

      <!-- Main Synchronized Panes Container -->
      <div class="tv-panes-stack flex-grow-1 position-relative" id="{chart_id}_stack">
        <!-- Vertical Synchronized Crosshair Tracking Line -->
        <div id="{chart_id}_vline" class="tv-crosshair-vline"></div>

        <!-- Ruler Measure Floating Box -->
        <div id="{chart_id}_ruler_box" class="tv-ruler-box d-none"></div>

        <!-- PANE 1: Candlestick Price + SMA 20/50 -->
        <div class="tv-pane-box" id="{chart_id}_pane_price">
          <div class="tv-pane-legend" id="{chart_id}_legend_price">
            <span class="tv-legend-badge text-white font-mono-num fw-bold">{ticker_clean}</span>
            <span class="ms-2" style="color: #f59e0b;">SMA 20: <span id="{chart_id}_val_sma20">-</span></span>
            <span class="ms-2" style="color: #3b82f6;">SMA 50: <span id="{chart_id}_val_sma50">-</span></span>
          </div>
          <div id="{chart_id}_chart_price"></div>
        </div>

        <!-- PANE 2: %B Indicator (0.0, 0.5, 1.0) -->
        <div class="tv-pane-box" id="{chart_id}_pane_pctb">
          <div class="tv-pane-legend" id="{chart_id}_legend_pctb">
            <span class="tv-legend-badge" style="color: #38bdf8;">%B: <span id="{chart_id}_val_pctb">-</span></span>
            <span class="ms-2 text-muted" style="font-size: 0.68rem;">(Acuan: 0.0 Oversold | 0.5 Tengah | 1.0 Overbought)</span>
          </div>
          <div id="{chart_id}_chart_pctb"></div>
        </div>

        <!-- PANE 3: RSI (14) Indicator -->
        <div class="tv-pane-box" id="{chart_id}_pane_rsi">
          <div class="tv-pane-legend" id="{chart_id}_legend_rsi">
            <span class="tv-legend-badge" style="color: #eab308;">RSI 14: <span id="{chart_id}_val_rsi">-</span></span>
            <span class="ms-2 text-muted" style="font-size: 0.68rem;">(Oversold: 30 | Overbought: 70)</span>
          </div>
          <div id="{chart_id}_chart_rsi"></div>
        </div>

        <!-- PANE 4: MACD (12, 26, 9) -->
        <div class="tv-pane-box" id="{chart_id}_pane_macd">
          <div class="tv-pane-legend" id="{chart_id}_legend_macd">
            <span class="tv-legend-badge text-white">MACD:</span>
            <span class="ms-1" style="color: #38bdf8;">Line: <span id="{chart_id}_val_macdl">-</span></span>
            <span class="ms-2" style="color: #f59e0b;">Signal: <span id="{chart_id}_val_macds">-</span></span>
            <span class="ms-2">Hist: <span id="{chart_id}_val_macdh">-</span></span>
          </div>
          <div id="{chart_id}_chart_macd"></div>
        </div>

        <!-- PANE 5: ATR (14) Volatility -->
        <div class="tv-pane-box" id="{chart_id}_pane_atr">
          <div class="tv-pane-legend" id="{chart_id}_legend_atr">
            <span class="tv-legend-badge" style="color: #f43f5e;">ATR 14: <span id="{chart_id}_val_atr">-</span></span>
            <span class="ms-2 text-muted" style="font-size: 0.68rem;">(Volatilitas Target TP 2× &amp; SL 1×)</span>
          </div>
          <div id="{chart_id}_chart_atr"></div>
        </div>

        <!-- PANE 6 (Backtest Only): Equity Curve Strategi vs Buy & Hold -->
        {"<!-- PANE 6: Equity Curve -->" if is_backtest else ""}
        {f'''
        <div class="tv-pane-box" id="{chart_id}_pane_equity">
          <div class="tv-pane-legend" id="{chart_id}_legend_equity">
            <span class="tv-legend-badge" style="color: #38bdf8;">Modal Strategi: <span id="{chart_id}_val_eqs">-</span></span>
            <span class="ms-3 text-muted">Buy &amp; Hold: <span id="{chart_id}_val_eqb">-</span></span>
          </div>
          <div id="{chart_id}_chart_equity"></div>
        </div>
        ''' if is_backtest else ""}
      </div>
    </div>

    <!-- Bottom Bar: Date Range / Zoom Selector + TradingView Interaction Tips -->
    <div class="tv-bottom-bar d-flex align-items-center justify-content-between flex-wrap px-3 py-1 gap-2">
      <!-- Date Range (Zoom) Buttons -->
      <div class="d-flex align-items-center gap-2">
        <span class="text-muted"><i class="bi bi-calendar3 me-1"></i>Rentang Zoom:</span>
        <div class="btn-group btn-group-sm" role="group" aria-label="Zoom Range">
          <button type="button" class="btn tv-range-btn" data-range="1M" onclick="{chart_id}_setZoomRange('1M')">1 Bulan</button>
          <button type="button" class="btn tv-range-btn" data-range="3M" onclick="{chart_id}_setZoomRange('3M')">3 Bulan</button>
          <button type="button" class="btn tv-range-btn active" data-range="6M" onclick="{chart_id}_setZoomRange('6M')">6 Bulan</button>
          <button type="button" class="btn tv-range-btn" data-range="1Y" onclick="{chart_id}_setZoomRange('1Y')">1 Tahun</button>
          <button type="button" class="btn tv-range-btn" data-range="ALL" onclick="{chart_id}_setZoomRange('ALL')">Semua Data</button>
        </div>
      </div>

      <!-- Superchart Interaction Tips -->
      <div class="text-muted d-none d-lg-flex align-items-center gap-3" style="font-size: 0.7rem;">
        <span><i class="bi bi-mouse me-1 text-info"></i>Scroll Chart: Zoom Horizontal</span>
        <span><i class="bi bi-arrows-expand me-1 text-info"></i>Drag Sumbu Kanan: Stretch Skala Harga</span>
        <span><i class="bi bi-arrow-repeat me-1 text-info"></i>Double-Click Sumbu: Auto-Fit</span>
      </div>
    </div>
  </div>

  <!-- Plotly Fallback Container -->
  <div id="{chart_id}_plotly_view" class="tv-plotly-fallback d-none">
    {plotly_fallback_html}
  </div>
</div>

<script>
(function() {{
  const chartId = "{chart_id}";
  const allData = {data_json};
  const isBacktest = {is_backtest_js};

  let currentTf = '1D';
  let rawData = allData.timeframes[currentTf];

  let charts = [];
  let seriesList = {{}};
  let activeTool = 'crosshair';
  let customPriceLines = [];
  let rulerStart = null;

  let tvLoadTries = 0;
  function initWhenReady() {{
    if (typeof LightweightCharts === 'undefined') {{
      tvLoadTries += 1;
      if (tvLoadTries > 120) {{
        // CDN Lightweight Charts gagal dimuat (~6 detik): otomatis tampilkan grafik Plotly.
        window[chartId + "_switchMode"]('plotly');
        return;
      }}
      setTimeout(initWhenReady, 50);
      return;
    }}
    buildTradingViewSuperchart();
  }}

  function buildTradingViewSuperchart() {{
    const stackEl = document.getElementById(chartId + "_stack");
    if (!stackEl) return;

    const width = stackEl.clientWidth || 980;

    const commonOptions = {{
      width: width,
      layout: {{
        background: {{ type: 'solid', color: '#131722' }},
        textColor: '#d1d4dc',
        fontSize: 11,
        fontFamily: "'Inter', -apple-system, sans-serif"
      }},
      grid: {{
        vertLines: {{ color: '#1e222d' }},
        horzLines: {{ color: '#1e222d' }}
      }},
      crosshair: {{
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {{
          color: '#758696',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
          labelBackgroundColor: '#2a2e39',
        }},
        horzLine: {{
          color: '#758696',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
          labelBackgroundColor: '#2a2e39',
        }}
      }},
      rightPriceScale: {{
        borderColor: '#2a2e39',
        visible: true,
        autoScale: true,
      }},
      timeScale: {{
        borderColor: '#2a2e39',
        visible: false,
        timeVisible: true,
        secondsVisible: false,
      }},
      handleScroll: {{
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      }},
      handleScale: {{
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      }}
    }};

    // 1. PANE 1: Candlestick (Tinggi 350px)
    const cPrice = LightweightCharts.createChart(document.getElementById(chartId + "_chart_price"), {{
      ...commonOptions,
      height: 350
    }});

    const candleSeries = cPrice.addCandlestickSeries({{
      upColor: '#089981',
      downColor: '#f23645',
      borderUpColor: '#089981',
      borderDownColor: '#f23645',
      wickUpColor: '#089981',
      wickDownColor: '#f23645'
    }});
    candleSeries.setData(rawData.candles);

    const s20Series = cPrice.addLineSeries({{
      color: '#f59e0b',
      lineWidth: 1.5,
      priceLineVisible: false,
      crosshairMarkerVisible: true
    }});
    s20Series.setData(rawData.sma20);

    const s50Series = cPrice.addLineSeries({{
      color: '#3b82f6',
      lineWidth: 1.5,
      priceLineVisible: false,
      crosshairMarkerVisible: true
    }});
    s50Series.setData(rawData.sma50);

    // 2. PANE 2: %B (Tinggi 130px)
    const cPctB = LightweightCharts.createChart(document.getElementById(chartId + "_chart_pctb"), {{
      ...commonOptions,
      height: 130
    }});
    const pctbSeries = cPctB.addLineSeries({{
      color: '#38bdf8',
      lineWidth: 1.5,
      priceLineVisible: false
    }});
    pctbSeries.setData(rawData.pctb);
    pctbSeries.createPriceLine({{ price: 1.0, color: '#ef4444', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '1.0' }});
    pctbSeries.createPriceLine({{ price: 0.5, color: '#a855f7', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: '0.5' }});
    pctbSeries.createPriceLine({{ price: 0.0, color: '#22c55e', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '0.0' }});

    // 3. PANE 3: RSI (Tinggi 125px)
    const cRSI = LightweightCharts.createChart(document.getElementById(chartId + "_chart_rsi"), {{
      ...commonOptions,
      height: 125
    }});
    const rsiSeries = cRSI.addLineSeries({{
      color: '#eab308',
      lineWidth: 1.5,
      priceLineVisible: false
    }});
    rsiSeries.setData(rawData.rsi14);
    rsiSeries.createPriceLine({{ price: 70, color: '#ef4444', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '70' }});
    rsiSeries.createPriceLine({{ price: 30, color: '#22c55e', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '30' }});

    // 4. PANE 4: MACD (Tinggi 140px)
    const cMACD = LightweightCharts.createChart(document.getElementById(chartId + "_chart_macd"), {{
      ...commonOptions,
      height: 140
    }});
    const macdHistSeries = cMACD.addHistogramSeries({{
      priceLineVisible: false
    }});
    macdHistSeries.setData(rawData.macd_hist);
    const macdLineSeries = cMACD.addLineSeries({{ color: '#38bdf8', lineWidth: 1.5, priceLineVisible: false }});
    macdLineSeries.setData(rawData.macd_line);
    const macdSigSeries = cMACD.addLineSeries({{ color: '#f59e0b', lineWidth: 1.5, priceLineVisible: false }});
    macdSigSeries.setData(rawData.macd_signal);
    macdHistSeries.createPriceLine({{ price: 0, color: '#64748b', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, axisLabelVisible: true, title: '0' }});

    // 5. PANE 5: ATR (Tinggi 110px)
    const cATR = LightweightCharts.createChart(document.getElementById(chartId + "_chart_atr"), {{
      ...commonOptions,
      height: 110,
      timeScale: {{
        ...commonOptions.timeScale,
        visible: !isBacktest
      }}
    }});
    const atrSeries = cATR.addAreaSeries({{
      topColor: 'rgba(244, 63, 94, 0.28)',
      bottomColor: 'rgba(244, 63, 94, 0.02)',
      lineColor: '#f43f5e',
      lineWidth: 1.5,
      priceLineVisible: false
    }});
    atrSeries.setData(rawData.atr14);

    charts = [cPrice, cPctB, cRSI, cMACD, cATR];
    seriesList = {{
      candles: candleSeries,
      s20: s20Series,
      s50: s50Series,
      pctb: pctbSeries,
      rsi: rsiSeries,
      macd_h: macdHistSeries,
      macd_l: macdLineSeries,
      macd_s: macdSigSeries,
      atr: atrSeries
    }};

    // Marker sinyal dipasang SETELAH semua series dibuat (menghindari TDZ pada const).
    if (rawData.entry_markers && rawData.entry_markers.length > 0) {{
      candleSeries.setMarkers(rawData.entry_markers);
    }}
    if (rawData.indicator_markers && rawData.indicator_markers.length > 0) {{
      pctbSeries.setMarkers(rawData.indicator_markers);
      rsiSeries.setMarkers(rawData.indicator_markers);
      macdLineSeries.setMarkers(rawData.indicator_markers);
    }}

    // 6. PANE 6 (Opsional untuk Backtest): Equity Curve (Tinggi 140px)
    if (isBacktest && document.getElementById(chartId + "_chart_equity")) {{
      const cEquity = LightweightCharts.createChart(document.getElementById(chartId + "_chart_equity"), {{
        ...commonOptions,
        height: 140,
        timeScale: {{
          ...commonOptions.timeScale,
          visible: true
        }}
      }});
      const eqStrat = cEquity.addLineSeries({{ color: '#38bdf8', lineWidth: 2, priceLineVisible: false }});
      eqStrat.setData(rawData.equity_strat);
      const eqBh = cEquity.addLineSeries({{ color: '#94a3b8', lineWidth: 1.2, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false }});
      eqBh.setData(rawData.equity_bh);

      charts.push(cEquity);
      seriesList.equity_s = eqStrat;
      seriesList.equity_b = eqBh;
    }}

    // SINKRONISASI 1: HORIZONTAL ZOOM & PAN ACROSS ALL PANES
    let isSyncingRange = false;
    charts.forEach((srcChart, i) => {{
      srcChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
        if (isSyncingRange || !range) return;
        isSyncingRange = true;
        charts.forEach((targetChart, j) => {{
          if (i !== j) {{
            targetChart.timeScale().setVisibleLogicalRange(range);
          }}
        }});
        isSyncingRange = false;
      }});
    }});

    // SINKRONISASI 2: VERTICAL TRACKING LINE & REACTIVE MULTI-PANE LEGENDS
    const vLine = document.getElementById(chartId + "_vline");

    function updateLegends(candle, s20, s50, pctb, rsi, ml, ms, mh, atr, eqs, eqb) {{
      const oEl = document.getElementById(chartId + "_o");
      const hEl = document.getElementById(chartId + "_h");
      const lEl = document.getElementById(chartId + "_l");
      const cEl = document.getElementById(chartId + "_c");
      const chgEl = document.getElementById(chartId + "_chg");

      if (candle) {{
        oEl.innerText = candle.open ? candle.open.toLocaleString('id-ID') : '-';
        hEl.innerText = candle.high ? candle.high.toLocaleString('id-ID') : '-';
        lEl.innerText = candle.low ? candle.low.toLocaleString('id-ID') : '-';
        cEl.innerText = candle.close ? candle.close.toLocaleString('id-ID') : '-';

        if (candle.open && candle.close) {{
          const diff = candle.close - candle.open;
          const pct = (diff / candle.open) * 100;
          const sign = diff >= 0 ? '+' : '';
          chgEl.innerText = sign + diff.toLocaleString('id-ID') + ' (' + sign + pct.toFixed(2) + '%)';
          chgEl.className = 'ms-2 tv-chg ' + (diff >= 0 ? 'text-success' : 'text-danger');
        }}
      }}

      const valS20 = document.getElementById(chartId + "_val_sma20");
      if (valS20) valS20.innerText = s20 ? s20.toLocaleString('id-ID') : '-';
      const valS50 = document.getElementById(chartId + "_val_sma50");
      if (valS50) valS50.innerText = s50 ? s50.toLocaleString('id-ID') : '-';

      const valPctB = document.getElementById(chartId + "_val_pctb");
      if (valPctB) valPctB.innerText = (pctb !== null && pctb !== undefined) ? Number(pctb).toFixed(4) : '-';

      const valRsi = document.getElementById(chartId + "_val_rsi");
      if (valRsi) valRsi.innerText = (rsi !== null && rsi !== undefined) ? Number(rsi).toFixed(2) : '-';

      const valMl = document.getElementById(chartId + "_val_macdl");
      if (valMl) valMl.innerText = (ml !== null && ml !== undefined) ? Number(ml).toFixed(2) : '-';
      const valMs = document.getElementById(chartId + "_val_macds");
      if (valMs) valMs.innerText = (ms !== null && ms !== undefined) ? Number(ms).toFixed(2) : '-';
      const valMh = document.getElementById(chartId + "_val_macdh");
      if (valMh) {{
        valMh.innerText = (mh !== null && mh !== undefined) ? Number(mh).toFixed(2) : '-';
        valMh.style.color = mh >= 0 ? '#089981' : '#f23645';
      }}

      const valAtr = document.getElementById(chartId + "_val_atr");
      if (valAtr) valAtr.innerText = (atr !== null && atr !== undefined) ? Number(atr).toLocaleString('id-ID') : '-';

      const valEqs = document.getElementById(chartId + "_val_eqs");
      if (valEqs && eqs !== null && eqs !== undefined) valEqs.innerText = Number(eqs).toFixed(4);
      const valEqb = document.getElementById(chartId + "_val_eqb");
      if (valEqb && eqb !== null && eqb !== undefined) valEqb.innerText = Number(eqb).toFixed(4);
    }}

    charts.forEach(c => {{
      c.subscribeCrosshairMove(param => {{
        if (!param || !param.point || param.point.x < 0) {{
          if (vLine) vLine.style.display = 'none';
          return;
        }}

        if (vLine) {{
          vLine.style.display = 'block';
          vLine.style.left = param.point.x + 'px';
        }}

        const candleData = param.seriesData.get(candleSeries);
        const s20Val = param.seriesData.get(s20Series)?.value;
        const s50Val = param.seriesData.get(s50Series)?.value;
        const pctbVal = param.seriesData.get(pctbSeries)?.value;
        const rsiVal = param.seriesData.get(rsiSeries)?.value;
        const mlVal = param.seriesData.get(macdLineSeries)?.value;
        const msVal = param.seriesData.get(macdSigSeries)?.value;
        const mhVal = param.seriesData.get(macdHistSeries)?.value;
        const atrVal = param.seriesData.get(atrSeries)?.value;
        const eqsVal = seriesList.equity_s ? param.seriesData.get(seriesList.equity_s)?.value : null;
        const eqbVal = seriesList.equity_b ? param.seriesData.get(seriesList.equity_b)?.value : null;

        updateLegends(candleData, s20Val, s50Val, pctbVal, rsiVal, mlVal, msVal, mhVal, atrVal, eqsVal, eqbVal);
      }});
    }});

    stackEl.addEventListener('mouseleave', () => {{
      if (vLine) vLine.style.display = 'none';
    }});

    // Set Default 6M Zoom View pada Timeframe Harian 1D
    window.{chart_id}_setZoomRange('6M');

    // Tangani Responsif Layar
    const ro = new ResizeObserver(entries => {{
      for (let entry of entries) {{
        const newW = entry.contentRect.width;
        if (newW > 100) {{
          charts.forEach(c => c.applyOptions({{ width: newW }}));
        }}
      }}
    }});
    ro.observe(stackEl);
  }}

  // ================================================================
  // 1. KONTROL TIMEFRAME CANDLE (1D, 1W, 1M)
  // ================================================================
  window.{chart_id}_setTimeframe = function(tfKey) {{
    if (!allData.timeframes || !allData.timeframes[tfKey]) return;
    currentTf = tfKey;
    rawData = allData.timeframes[tfKey];

    // Update Tombol Timeframe Aktif
    document.querySelectorAll('#{chart_id}_wrapper .tv-tf-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById('{chart_id}_tf_' + tfKey);
    if (activeBtn) activeBtn.classList.add('active');

    // Update Badge Interval
    const badge = document.getElementById('{chart_id}_interval_badge');
    if (badge) badge.innerText = tfKey;

    // Update Keterangan Pengertian Timeframe
    const infoPill = document.getElementById('{chart_id}_tf_info');
    if (infoPill) {{
      if (tfKey === '1D') {{
        infoPill.innerHTML = "<i class='bi bi-calendar-day me-1 text-info'></i>1 Lilin = 1 Hari (Daily)";
      }} else if (tfKey === '1W') {{
        infoPill.innerHTML = "<i class='bi bi-calendar-week me-1 text-warning'></i>1 Lilin = 1 Minggu (Weekly)";
      }} else if (tfKey === '1M') {{
        infoPill.innerHTML = "<i class='bi bi-calendar-month me-1 text-success'></i>1 Lilin = 1 Bulan (Monthly)";
      }}
    }}

    // Update Seluruh Series dengan Data Timeframe Baru
    if (seriesList.candles) seriesList.candles.setData(rawData.candles || []);
    if (seriesList.s20) seriesList.s20.setData(rawData.sma20 || []);
    if (seriesList.s50) seriesList.s50.setData(rawData.sma50 || []);
    if (seriesList.pctb) seriesList.pctb.setData(rawData.pctb || []);
    if (seriesList.rsi) seriesList.rsi.setData(rawData.rsi14 || []);
    if (seriesList.macd_l) seriesList.macd_l.setData(rawData.macd_line || []);
    if (seriesList.macd_s) seriesList.macd_s.setData(rawData.macd_signal || []);
    if (seriesList.macd_h) seriesList.macd_h.setData(rawData.macd_hist || []);
    if (seriesList.atr) seriesList.atr.setData(rawData.atr14 || []);
    if (seriesList.equity_s && rawData.equity_strat) seriesList.equity_s.setData(rawData.equity_strat);
    if (seriesList.equity_b && rawData.equity_bh) seriesList.equity_b.setData(rawData.equity_bh);

    // Update Markers
    if (seriesList.candles) {{
      seriesList.candles.setMarkers(rawData.entry_markers || []);
    }}
    if (seriesList.pctb) {{
      seriesList.pctb.setMarkers(rawData.indicator_markers || []);
    }}
    if (seriesList.rsi) {{
      seriesList.rsi.setMarkers(rawData.indicator_markers || []);
    }}
    if (seriesList.macd_l) {{
      seriesList.macd_l.setMarkers(rawData.indicator_markers || []);
    }}

    // Fit content & Auto Scale
    charts.forEach(c => c.timeScale().fitContent());
    charts.forEach(c => c.priceScale('right').applyOptions({{ autoScale: true }}));

    // Reset tombol zoom ke ALL saat pindah resolusi
    document.querySelectorAll('#{chart_id}_wrapper .tv-range-btn').forEach(b => b.classList.remove('active'));
  }};

  // ================================================================
  // 2. KONTROL RENTANG ZOOM WAKTU (1 Bulan, 3 Bulan, 6 Bulan, dst)
  // ================================================================
  window.{chart_id}_setZoomRange = function(rangeKey) {{
    if (!charts.length) return;
    document.querySelectorAll('#{chart_id}_wrapper .tv-range-btn').forEach(b => {{
      b.classList.toggle('active', b.dataset.range === rangeKey);
    }});

    const total = rawData.candles.length;
    if (total === 0) return;

    if (rangeKey === 'ALL') {{
      charts[0].timeScale().fitContent();
      return;
    }}

    let bars = total;
    if (currentTf === '1D') {{
      if (rangeKey === '1M') bars = 22;
      else if (rangeKey === '3M') bars = 65;
      else if (rangeKey === '6M') bars = 125;
      else if (rangeKey === '1Y') bars = 250;
    }} else if (currentTf === '1W') {{
      if (rangeKey === '1M') bars = 4;
      else if (rangeKey === '3M') bars = 13;
      else if (rangeKey === '6M') bars = 26;
      else if (rangeKey === '1Y') bars = 52;
    }} else if (currentTf === '1M') {{
      if (rangeKey === '1M') bars = 2;
      else if (rangeKey === '3M') bars = 3;
      else if (rangeKey === '6M') bars = 6;
      else if (rangeKey === '1Y') bars = 12;
    }}

    const fromIdx = Math.max(0, total - bars);
    const toIdx = total - 1;
    charts[0].timeScale().setVisibleLogicalRange({{ from: fromIdx, to: toIdx }});
  }};

  window.{chart_id}_resetView = function() {{
    if (charts.length) {{
      charts.forEach(c => c.timeScale().fitContent());
      charts.forEach(c => c.priceScale('right').applyOptions({{ autoScale: true }}));
      document.querySelectorAll('#{chart_id}_wrapper .tv-range-btn').forEach(b => b.classList.remove('active'));
    }}
  }};

  window.{chart_id}_toggleFullscreen = function() {{
    const el = document.getElementById(chartId + "_tv_view");
    if (!document.fullscreenElement) {{
      el.requestFullscreen().catch(() => {{}});
    }} else {{
      document.exitFullscreen();
    }}
  }};

  window.{chart_id}_setTool = function(tool) {{
    activeTool = tool;
    document.querySelectorAll('#{chart_id}_wrapper .tv-tool-btn').forEach(btn => btn.classList.remove('active'));
    const btn = document.getElementById('{chart_id}_tool_' + tool);
    if (btn) btn.classList.add('active');

    const stack = document.getElementById(chartId + "_stack");
    if (!stack) return;

    if (tool === 'crosshair') {{
      stack.style.cursor = 'crosshair';
      charts.forEach(c => c.applyOptions({{ crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }} }}));
    }} else if (tool === 'ruler') {{
      stack.style.cursor = 'cell';
    }} else if (tool === 'hline') {{
      stack.style.cursor = 'row-resize';
    }}
  }};

  // Listener Klik untuk Ruler & Horizontal Line (koordinat relatif pane harga)
  document.getElementById(chartId + "_stack")?.addEventListener('click', function(e) {{
    if (activeTool !== 'hline' && activeTool !== 'ruler') return;

    const priceEl = document.getElementById(chartId + "_chart_price");
    if (!priceEl) return;
    const rect = priceEl.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientX > rect.right ||
        e.clientY < rect.top || e.clientY > rect.bottom) return;

    const xRel = e.clientX - rect.left;
    const yRel = e.clientY - rect.top;
    const priceNum = seriesList.candles.coordinateToPrice(yRel);

    if (activeTool === 'hline') {{
      if (priceNum) {{
        const line = seriesList.candles.createPriceLine({{
          price: priceNum,
          color: '#f59e0b',
          lineWidth: 1.5,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'H-Line ' + priceNum.toLocaleString('id-ID')
        }});
        customPriceLines.push(line);
      }}
      window.{chart_id}_setTool('crosshair');
      return;
    }}

    // RULER: klik pertama = titik awal, klik kedua = hasil pengukuran (selisih harga, %, jumlah bar)
    const rulerBox = document.getElementById(chartId + "_ruler_box");
    const stackRect = this.getBoundingClientRect();
    const boxLeft = (rect.left - stackRect.left) + xRel + 12;
    const boxTop = (rect.top - stackRect.top) + yRel + 12;
    const logical = charts[0].timeScale().coordinateToLogical(xRel);

    if (!rulerStart) {{
      rulerStart = {{ price: priceNum, logical: logical }};
      if (rulerBox) {{
        rulerBox.classList.remove('d-none');
        rulerBox.style.left = boxLeft + 'px';
        rulerBox.style.top = boxTop + 'px';
        rulerBox.innerHTML = "<span class='text-info'><i class='bi bi-rulers me-1'></i>Klik titik kedua untuk mengukur...</span>";
      }}
      return;
    }}

    const barCount = Math.abs(Math.round((logical || 0) - (rulerStart.logical || 0)));
    const delta = (priceNum || 0) - (rulerStart.price || 0);
    const pct = rulerStart.price ? (delta / rulerStart.price) * 100 : 0;
    const sign = delta >= 0 ? '+' : '';
    const warna = delta >= 0 ? 'text-success' : 'text-danger';

    if (rulerBox) {{
      rulerBox.style.left = boxLeft + 'px';
      rulerBox.style.top = boxTop + 'px';
      rulerBox.innerHTML =
        "<span class='fw-bold " + warna + "'>" + sign +
        delta.toLocaleString('id-ID', {{ maximumFractionDigits: 2 }}) +
        " (" + sign + pct.toFixed(2) + "%)</span>" +
        "<span class='text-muted ms-2'>" + barCount + " bar</span>";
    }}
    rulerStart = null;
  }});

  window.{chart_id}_clearDrawings = function() {{
    if (seriesList.candles && customPriceLines.length) {{
      customPriceLines.forEach(l => seriesList.candles.removePriceLine(l));
      customPriceLines = [];
    }}
    const rulerBox = document.getElementById(chartId + "_ruler_box");
    if (rulerBox) rulerBox.classList.add('d-none');
    rulerStart = null;
  }};

  window.{chart_id}_switchMode = function(mode) {{
    const tvView = document.getElementById(chartId + "_tv_view");
    const plotlyView = document.getElementById(chartId + "_plotly_view");
    const btnTv = document.getElementById(chartId + "_btn_tv");
    const btnPlotly = document.getElementById(chartId + "_btn_plotly");

    if (mode === 'plotly') {{
      tvView.classList.add('d-none');
      plotlyView.classList.remove('d-none');
      btnTv.classList.remove('active');
      btnPlotly.classList.add('active');
      // Plotly dirender saat tersembunyi, jadi ukuran kanvas perlu dihitung ulang.
      if (window.Plotly && plotlyView) {{
        requestAnimationFrame(() => {{
          plotlyView.querySelectorAll('.plotly-graph-div').forEach(el => window.Plotly.Plots.resize(el));
        }});
      }}
    }} else {{
      plotlyView.classList.add('d-none');
      tvView.classList.remove('d-none');
      btnPlotly.classList.remove('active');
      btnTv.classList.add('active');
      charts.forEach(c => c.timeScale().fitContent());
    }}
  }};

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initWhenReady);
  }} else {{
    initWhenReady();
  }}
}})();
</script>
"""
    return html
