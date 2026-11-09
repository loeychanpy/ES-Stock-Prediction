"""Signal validation and event-driven backtest for the stock expert system.

Usage:
    python src/signal_validation_backtest.py BBCA
    python src/signal_validation_backtest.py --all
    python src/signal_validation_backtest.py BBCA --save-details

Signal is formed after close on day t and executed at Open on day t+1.
Only historical bars strictly before t are used for the N-day low reference.
This is an educational historical simulation, not investment advice.
"""
from __future__ import annotations
import argparse
import json
import os
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from fuzzy_engine import infer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "storage_data", "2_inference_ready")
OUT_DIR = os.path.join(ROOT, "storage_data", "4_backtesting")
BUY_FEE = 0.0015
SELL_FEE = 0.0025


def validate_signals(df: pd.DataFrame, n_days: int = 5,
                     near_pct: float = 0.03) -> pd.DataFrame:
    """Build NPMM-inspired local-low + SMA trend filter without look-ahead.

    The reference is the minimum Low of the PREVIOUS N completed sessions
    (shift(1)); current-day data is not part of the reference window.
    Current Close must be no more than near_pct above that reference.
    """
    if n_days < 2 or near_pct < 0:
        raise ValueError("n_days harus >= 2 dan near_pct tidak boleh negatif")
    out = df.copy().sort_index()
    required = {"Open", "High", "Low", "Close", "SMA_20", "SMA_50", "ATR_14"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ada: {sorted(missing)}")
    prior_n_day_low = out["Low"].rolling(n_days, min_periods=n_days).min().shift(1)
    out["Prior_N_Day_Low"] = prior_n_day_low
    out["Local_Min_Valid"] = out["Close"].le(prior_n_day_low * (1 + near_pct))
    out["Trend_Valid"] = out["SMA_20"].gt(out["SMA_50"])
    out["Signal_Valid_Recalc"] = (
        out["Local_Min_Valid"] & out["Trend_Valid"] & prior_n_day_low.notna()
    )
    return out


def evaluate_npmm_proximity(detail: pd.DataFrame, n_days: int = 5,
                            tol_pct: float = 0.03) -> dict:
    """Evaluasi historis kedekatan sinyal BELI dengan titik minimum lokal NPMM.

    Mengacu bagian ANALISA laporan: label NPMM historis (jendela simetris N hari)
    digunakan hanya pada evaluasi historis (terpisah dari metrik keuangan) untuk
    mengukur seberapa dekat sinyal BELI dengan titik minimum harga sebenarnya.
    """
    window = 2 * n_days + 1
    npmm_min_price = detail["Low"].rolling(window=window, center=True, min_periods=n_days).min()
    dist_pct = ((detail["Close"] - npmm_min_price) / npmm_min_price).clip(lower=0.0)
    buy_rows = detail[detail["Buy_Signal"]]
    if buy_rows.empty:
        return {
            "buy_signals_evaluated": 0,
            "avg_distance_to_npmm_min_pct": 0.0,
            "near_npmm_min_hit_rate_pct": 0.0,
        }
    buy_dist = dist_pct.loc[buy_rows.index].dropna()
    hits = (buy_dist <= tol_pct).sum()
    return {
        "buy_signals_evaluated": int(len(buy_dist)),
        "avg_distance_to_npmm_min_pct": round(float(buy_dist.mean() * 100), 2) if len(buy_dist) else 0.0,
        "near_npmm_min_hit_rate_pct": round(float(hits / len(buy_dist) * 100), 2) if len(buy_dist) else 0.0,
    }


def _facts(row: pd.Series, atr_tp_mult: float, atr_sl_mult: float) -> dict:
    close, atr = float(row.Close), float(row.ATR_14)
    return {
        "fuzzy_inputs": {
            "rsi_14": float(row.RSI_14), "macd_hist": float(row.MACD_Hist),
            "bb_pct_b": float(row.BB_PctB), "volume_ratio": float(row.Volume_Ratio),
        },
        "validation_filter": {"signal_valid": bool(row.Signal_Valid_Recalc)},
        "risk_management": {
            "initial_tp_estimate": close + atr_tp_mult * atr,
            "initial_sl_estimate": close - atr_sl_mult * atr,
        },
        "price_volume": {"close": close, "open": float(row.Open),
                         "high": float(row.High), "low": float(row.Low),
                         "volume": int(row.Volume)},
    }


def _build_signal_snapshot(sig_row: pd.Series, inf_result: dict) -> dict:
    """Susun rekaman lengkap seluruh indikator, filter, dan aturan fuzzy pada saat sinyal muncul."""
    prior_low = float(sig_row.Prior_N_Day_Low) if pd.notna(sig_row.Prior_N_Day_Low) else float(sig_row.Low)
    close_val = float(sig_row.Close)
    dist_low_pct = ((close_val - prior_low) / prior_low * 100.0) if prior_low > 0 else 0.0

    return {
        "ohlcv": {
            "open": round(float(sig_row.Open), 2),
            "high": round(float(sig_row.High), 2),
            "low": round(float(sig_row.Low), 2),
            "close": round(close_val, 2),
            "volume": int(sig_row.Volume),
        },
        "indicators": {
            "rsi_14": round(float(sig_row.RSI_14), 2),
            "macd_line": round(float(sig_row.MACD_Line), 2) if "MACD_Line" in sig_row else 0.0,
            "macd_signal": round(float(sig_row.MACD_Signal), 2) if "MACD_Signal" in sig_row else 0.0,
            "macd_hist": round(float(sig_row.MACD_Hist), 2),
            "bb_upper": round(float(sig_row.BB_Upper), 2) if "BB_Upper" in sig_row else 0.0,
            "bb_middle": round(float(sig_row.BB_Middle), 2) if "BB_Middle" in sig_row else 0.0,
            "bb_lower": round(float(sig_row.BB_Lower), 2) if "BB_Lower" in sig_row else 0.0,
            "bb_pct_b": round(float(sig_row.BB_PctB), 4),
            "volume_sma_20": int(sig_row.Volume_SMA_20) if "Volume_SMA_20" in sig_row and pd.notna(sig_row.Volume_SMA_20) else 0,
            "volume_ratio": round(float(sig_row.Volume_Ratio), 2),
            "sma_20": round(float(sig_row.SMA_20), 2),
            "sma_50": round(float(sig_row.SMA_50), 2),
            "atr_14": round(float(sig_row.ATR_14), 2),
            "prior_n_day_low": round(prior_low, 2),
            "dist_to_low_pct": round(dist_low_pct, 2),
        },
        "validation": {
            "trend_valid": bool(sig_row.Trend_Valid),
            "local_min_valid": bool(sig_row.Local_Min_Valid),
            "signal_valid": bool(sig_row.Signal_Valid_Recalc),
        },
        "fuzzified_inputs": inf_result.get("fuzzified_inputs", {}),
        "all_rules": inf_result.get("all_rules", []),
        "triggered_rules": inf_result.get("triggered_rules", []),
        "explanation": inf_result.get("explanation", ""),
    }


def _metrics(returns: list[float], equity_values: list[float], trades: list[dict],
             benchmark_return: float) -> dict:
    arr = np.asarray(returns, dtype=float)
    eq = pd.Series(equity_values, dtype=float)
    peak = eq.cummax() if len(eq) else eq
    dd = (eq / peak - 1.0) if len(eq) else pd.Series(dtype=float)
    return {
        "trades": len(trades),
        "wins": int((arr > 0).sum()),
        "losses": int((arr <= 0).sum()),
        "win_rate_pct": round(float((arr > 0).mean() * 100), 2) if len(arr) else 0.0,
        "total_return_pct": round((float(eq.iloc[-1]) - 1) * 100, 2) if len(eq) else 0.0,
        "max_drawdown_pct": round(float(dd.min() * 100), 2) if len(dd) else 0.0,
        "avg_trade_return_pct": round(float(arr.mean() * 100), 3) if len(arr) else 0.0,
        "buy_and_hold_return_pct": round(benchmark_return * 100, 2),
        "excess_vs_buy_hold_pct": round(((float(eq.iloc[-1]) - 1) - benchmark_return) * 100, 2) if len(eq) else 0.0,
    }


def backtest(df: pd.DataFrame, n_days: int = 5, near_pct: float = 0.03,
             atr_tp_mult: float = 3.0, atr_sl_mult: float = 1.5,
             buy_fee: float = BUY_FEE, sell_fee: float = SELL_FEE,
             start_date: str | None = None, end_date: str | None = None) -> dict:
    """Long-only, one position at a time; TP/SL tested against daily OHLC.

    If both TP and SL are touched in one candle, SL is assumed first (conservative).
    Gaps through a stop/target are filled at the open. Remaining position is
    liquidated at final Close. Equity curve marks daily close-to-close while
    flat and marks the position while invested.
    """
    if atr_tp_mult <= 0 or atr_sl_mult <= 0:
        raise ValueError("ATR multiplier harus positif")
    data = validate_signals(df, n_days, near_pct).dropna(subset=["Open", "High", "Low", "Close", "ATR_14"])
    if start_date:
        data = data.loc[pd.Timestamp(start_date):]
    if end_date:
        data = data.loc[:pd.Timestamp(end_date)]
    if len(data) < n_days + 3:
        raise ValueError("Data terlalu sedikit untuk backtest; tambah rentang data atau kecilkan N hari")

    decisions: dict[Any, dict] = {}
    for dt, row in data.iterrows():
        # Warm-up indicators must be present before fuzzy evaluation.
        fuzzy_cols = ["RSI_14", "MACD_Hist", "BB_PctB", "Volume_Ratio"]
        if row[fuzzy_cols].isna().any():
            continue
        result = infer(_facts(row, atr_tp_mult, atr_sl_mult))
        decisions[dt] = result

    trades: list[dict] = []
    daily_equity = []
    equity = 1.0
    position = None
    idx = list(data.index)
    for i, dt in enumerate(idx):
        row = data.loc[dt]
        # Manage an existing position using today's OHLC.
        if position is not None:
            exit_price, reason = None, None
            # Gap handling first, then intraday range. SL wins ambiguous candles.
            if row.Open <= position["sl"]:
                exit_price, reason = float(row.Open), "SL_GAP"
            elif row.Open >= position["tp"]:
                exit_price, reason = float(row.Open), "TP_GAP"
            else:
                hit_sl = row.Low <= position["sl"]
                hit_tp = row.High >= position["tp"]
                if hit_sl:
                    exit_price, reason = position["sl"], "SL" if not hit_tp else "SL_BOTH_TOUCHED"
                elif hit_tp:
                    exit_price, reason = position["tp"], "TP"
            if exit_price is not None or i == len(idx) - 1:
                if exit_price is None:
                    exit_price, reason = float(row.Close), "END_OF_DATA"
                gross_factor = exit_price / position["entry"]
                net_factor = gross_factor * (1 - sell_fee)
                trade_ret = net_factor * (1 - buy_fee) - 1
                equity *= (1 + trade_ret)
                trades.append({**position, "exit_date": dt, "exit_price": round(float(exit_price), 4),
                               "exit_reason": reason, "return_pct": round(trade_ret * 100, 3)})
                position = None
        # Entry from signal generated at yesterday's close, filled at today's open.
        if position is None and i > 0:
            prev_dt = idx[i - 1]
            prev_result = decisions.get(prev_dt)
            if prev_result and prev_result["decision"] == "BELI" and prev_result["signal_valid"]:
                prev_row = data.loc[prev_dt]
                entry = float(row.Open)
                atr = float(prev_row["ATR_14"])
                if np.isfinite(entry) and entry > 0 and np.isfinite(atr) and atr > 0:
                    position = {
                        "signal_date": prev_dt,
                        "entry_date": dt,
                        "entry": entry,
                        "tp": entry + atr_tp_mult * atr,
                        "sl": entry - atr_sl_mult * atr,
                        "signal_strength": prev_result["signal_strength"],
                        "snapshot": _build_signal_snapshot(prev_row, prev_result),
                    }
        # Mark-to-market equity for drawdown; approximate daily exposure return.
        if position is None:
            daily_equity.append(equity)
        else:
            mark = float(row.Close) / position["entry"] * (1 - buy_fee)
            daily_equity.append(equity * mark)

    # Benchmark uses the same selected period and round-trip transaction fees.
    first_open, last_close = float(data.Open.iloc[0]), float(data.Close.iloc[-1])
    benchmark = (last_close / first_open) * (1 - buy_fee) * (1 - sell_fee) - 1
    summary = _metrics([t["return_pct"] / 100 for t in trades], daily_equity, trades, benchmark)
    detail = data.copy()
    detail["Fuzzy_Decision"] = [decisions.get(d, {}).get("decision", "SKIP") for d in detail.index]
    detail["Signal_Strength"] = [decisions.get(d, {}).get("signal_strength", np.nan) for d in detail.index]
    detail["Fuzzy_Signal_Valid"] = [decisions.get(d, {}).get("signal_valid", False) for d in detail.index]
    detail["Buy_Signal"] = detail["Fuzzy_Decision"].eq("BELI") & detail["Signal_Valid_Recalc"]
    detail["Equity_Curve"] = np.round(daily_equity, 6)
    detail["Buy_Hold_Equity"] = np.round((detail["Close"] / first_open) * (1 - buy_fee), 6)

    npmm_eval = evaluate_npmm_proximity(detail, n_days=n_days, tol_pct=near_pct)
    summary.update({"n_days": len(data), "valid_signal_days": int(data.Signal_Valid_Recalc.sum()),
                    "fuzzy_buy_days": int(detail.Buy_Signal.sum()),
                    "npmm_evaluation": npmm_eval,
                    "parameters": {"n_days": n_days, "near_pct": near_pct,
                                   "atr_tp_mult": atr_tp_mult, "atr_sl_mult": atr_sl_mult,
                                   "buy_fee_pct": buy_fee * 100, "sell_fee_pct": sell_fee * 100},
                    "trades_detail": pd.DataFrame(trades), "daily_detail": detail})
    return summary


def calibrate_membership(df: pd.DataFrame, train_ratio: float = 0.7) -> dict:
    """Suggest data-scaled fuzzy breakpoints from TRAINING quantiles only.

    Quantile diagnostics are suggestions, not automatically applied to the
    production fuzzy engine. Test rows are deliberately excluded.
    """
    split = max(1, int(len(df) * train_ratio))
    train = df.iloc[:split]
    specs = {"rsi_14": ("RSI_14", [0.10, 0.35, 0.65, 0.90]),
             "macd_hist": ("MACD_Hist", [0.10, 0.35, 0.65, 0.90]),
             "bb_pct_b": ("BB_PctB", [0.10, 0.35, 0.65, 0.90]),
             "volume_ratio": ("Volume_Ratio", [0.10, 0.35, 0.65, 0.90])}
    result = {}
    for key, (col, qs) in specs.items():
        vals = train[col].dropna()
        result[key] = {f"q{int(q*100)}": round(float(vals.quantile(q)), 6) for q in qs}
    result["training_rows"] = split
    result["test_rows_excluded"] = len(df) - split
    result["note"] = "Gunakan kuantil sebagai kandidat; cek firing rule dan validasi pada data test sebelum menetapkan."
    return result


def calibrate_atr(df: pd.DataFrame, n_days: int = 5, near_pct: float = 0.03,
                  tp_grid=(2.0, 2.5, 3.0, 3.5, 4.0),
                  sl_grid=(1.0, 1.25, 1.5, 1.75, 2.0), train_ratio: float = 0.7) -> pd.DataFrame:
    """Grid-search ATR multipliers on chronological TRAINING data only."""
    split = max(n_days + 3, int(len(df) * train_ratio))
    train = df.iloc[:split]
    rows = []
    for tp, sl in product(tp_grid, sl_grid):
        try:
            r = backtest(train, n_days=n_days, near_pct=near_pct,
                         atr_tp_mult=tp, atr_sl_mult=sl)
            rows.append({"tp_atr": tp, "sl_atr": sl, "return_pct": r["total_return_pct"],
                         "win_rate_pct": r["win_rate_pct"], "max_drawdown_pct": r["max_drawdown_pct"],
                         "trades": r["trades"]})
        except ValueError:
            continue
    out = pd.DataFrame(rows)
    if not out.empty:
        # Simple transparent objective; penalizes drawdown and discourages tiny samples.
        out["objective"] = (out.return_pct + out.max_drawdown_pct).round(2)
        out = out.sort_values(["objective", "trades"], ascending=[False, False]).reset_index(drop=True)
    return out


def run_one(code: str, save_details: bool = False) -> dict:
    path = os.path.join(DATA_DIR, f"{code.upper()}_clean_indicators.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path, index_col="Date", parse_dates=True).sort_index()
    result = backtest(df)
    print(f"\n===== BACKTEST {code.upper()} =====")
    for k, v in result.items():
        if k not in {"trades_detail", "daily_detail"}:
            print(f"{k}: {v}")
    print("\nMembership calibration (training quantiles):")
    print(json.dumps(calibrate_membership(df), indent=2))
    atr_cal = calibrate_atr(df)
    print("\nATR multiplier candidates (TRAIN only):")
    print(atr_cal.head(10).to_string(index=False) if not atr_cal.empty else "Tidak ada kombinasi yang dapat diuji")
    if save_details:
        os.makedirs(OUT_DIR, exist_ok=True)
        trades_csv_df = result["trades_detail"].drop(columns=["snapshot"], errors="ignore")
        trades_csv_df.to_csv(os.path.join(OUT_DIR, f"{code.upper()}_trades.csv"), index=False)
        result["daily_detail"].to_csv(os.path.join(OUT_DIR, f"{code.upper()}_daily.csv"))
        atr_cal.to_csv(os.path.join(OUT_DIR, f"{code.upper()}_atr_calibration.csv"), index=False)
        with open(os.path.join(OUT_DIR, f"{code.upper()}_membership_calibration.json"), "w") as f:
            json.dump(calibrate_membership(df), f, indent=2)
        print(f"\nDetail disimpan di: {OUT_DIR}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Signal validation & backtesting")
    parser.add_argument("codes", nargs="*", help="Kode saham, contoh BBCA BBRI TLKM")
    parser.add_argument("--all", action="store_true", help="Proses semua CSV saham")
    parser.add_argument("--save-details", action="store_true", help="Simpan transaksi dan kalibrasi")
    args = parser.parse_args()
    if args.all:
        codes = [f.replace("_clean_indicators.csv", "") for f in os.listdir(DATA_DIR)
                 if f.endswith("_clean_indicators.csv")]
    else:
        codes = args.codes
    if not codes:
        parser.error("Masukkan kode saham atau gunakan --all")
    for stock in codes:
        run_one(stock, args.save_details)
