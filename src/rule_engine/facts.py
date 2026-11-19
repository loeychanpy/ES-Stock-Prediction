"""Helper untuk menyusun fakta inferensi dari DataFrame indikator (t, t-1, t-2)."""

import pandas as pd

INDICATOR_COLS = {"rsi_14": "RSI_14", "macd_hist": "MACD_Hist", "bb_pct_b": "BB_PctB"}


def _inputs(row: pd.Series | None) -> dict:
    if row is None:
        return {}
    vals = {k: row.get(col) for k, col in INDICATOR_COLS.items()}
    if any(v is None or pd.isna(v) for v in vals.values()):
        return {}
    return {k: float(v) for k, v in vals.items()}


def build_facts(df: pd.DataFrame, pos: int, signal_valid: bool,
                atr_tp_mult: float = 2.0, atr_sl_mult: float = 1.0) -> dict:
    """Bangun facts untuk baris ke-`pos` (posisi integer) pada df yang sudah terurut."""
    row = df.iloc[pos]
    prev = df.iloc[pos - 1] if pos >= 1 else None
    prev2 = df.iloc[pos - 2] if pos >= 2 else None
    close, atr = float(row["Close"]), float(row["ATR_14"])
    return {
        "indicator_inputs": _inputs(row),
        "previous_inputs": _inputs(prev),
        "previous2_inputs": _inputs(prev2),
        "validation_filter": {"signal_valid": bool(signal_valid)},
        "risk_management": {
            "initial_tp_estimate": round(close + atr_tp_mult * atr, 2),
            "initial_sl_estimate": round(close - atr_sl_mult * atr, 2),
        },
        "price_volume": {
            "close": close, "open": float(row["Open"]),
            "high": float(row["High"]), "low": float(row["Low"]),
            "volume": int(row["Volume"]),
        },
    }


def attach_previous_inputs(facts: dict, df: pd.DataFrame) -> dict:
    """Lengkapi facts JSON (hari terakhir) dengan nilai indikator t-1 dan t-2 dari CSV."""
    if not facts or df is None or len(df) < 2:
        return facts
    df = df.sort_index()
    facts = dict(facts)
    facts.setdefault("indicator_inputs", facts.get("fuzzy_inputs", {}))
    facts["previous_inputs"] = _inputs(df.iloc[-2])
    facts["previous2_inputs"] = _inputs(df.iloc[-3]) if len(df) >= 3 else {}
    return facts
