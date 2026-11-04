"""Research-only multi-pair signal scanner. No broker connections or orders.

Input: CSVs with UTC time,open,high,low,close for each symbol.
Only completed candles are used; scores are comparable but NOT calibrated
probabilities. Use the next bar for any hypothetical execution.
"""
import argparse
import json
import math
from pathlib import Path

import pandas as pd

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "AUDUSD")


def scan_symbol(frame, symbol):
    if symbol not in SYMBOLS:
        raise ValueError("Unsupported research symbol")
    required = {"time", "open", "high", "low", "close"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    d = frame.copy()
    d["time"] = pd.to_datetime(d["time"], utc=True, errors="raise")
    if d.time.isna().any() or d.time.duplicated().any():
        raise ValueError("Missing or duplicate timestamps")
    d = d.sort_values("time").reset_index(drop=True)
    if len(d) < 220:
        raise ValueError("At least 220 completed candles required")
    for c in ("open", "high", "low", "close"):
        d[c] = pd.to_numeric(d[c], errors="raise")
        if not d[c].map(math.isfinite).all() or (d[c] <= 0).any():
            raise ValueError("Prices must be positive and finite")
    if ((d.high < d[["open", "close", "low"]].max(axis=1)) |
            (d.low > d[["open", "close"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC")
    close = d.close
    fast = close.ewm(span=20, adjust=False).mean()
    slow = close.ewm(span=50, adjust=False).mean()
    tr = pd.concat([d.high - d.low, (d.high - close.shift()).abs(),
                    (d.low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    i = len(d) - 1
    buy = fast.iloc[i] > slow.iloc[i] and close.iloc[i-1] <= fast.iloc[i-1] and close.iloc[i] > fast.iloc[i]
    sell = fast.iloc[i] < slow.iloc[i] and close.iloc[i-1] >= fast.iloc[i-1] and close.iloc[i] < fast.iloc[i]
    side = "BUY" if buy else "SELL" if sell else None
    volatility = float(atr.iloc[i])
    score = abs(float(fast.iloc[i] - slow.iloc[i])) / volatility if volatility > 0 else 0.0
    return {"symbol": symbol, "completed_candle_utc": d.time.iloc[i].isoformat(),
            "signal": side, "score_atr_units": round(score, 6) if side else None,
            "note": "Research ranking only; not a win probability or execution instruction"}


def scan_files(files):
    """Return strongest triggered setup first; all inputs must share a bar timestamp."""
    results = [scan_symbol(pd.read_csv(path), symbol) for symbol, path in files.items()]
    if len({r["completed_candle_utc"] for r in results}) > 1:
        raise ValueError("Symbols have mismatched last completed candle timestamps")
    return sorted((r for r in results if r["signal"]), key=lambda r: (-r["score_atr_units"], r["symbol"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for symbol in SYMBOLS:
        parser.add_argument("--" + symbol.lower(), type=Path)
    args = parser.parse_args()
    files = {s: getattr(args, s.lower()) for s in SYMBOLS if getattr(args, s.lower()) is not None}
    if not files:
        parser.error("Supply at least one symbol CSV, e.g. --eurusd EURUSD.csv")
    print(json.dumps(scan_files(files), indent=2))
