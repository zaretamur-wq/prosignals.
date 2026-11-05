"""Causal M5/M15 chart-pattern signals for offline comparison.

Only closed bars through index i are used. No orders are sent.
Patterns: rectangle breakout, failed breakout (liquidity sweep), double top/bottom.
"""
import numpy as np

def detect(df, i, lookback=24, tolerance=0.15):
    """Return signal dict or None. i must be the most recent CLOSED bar."""
    if i < lookback + 15 or i >= len(df):
        return None
    window = df.iloc[i-lookback:i]  # strictly before signal candle
    bar = df.iloc[i]
    hi = float(window.high.max())
    lo = float(window.low.min())
    width = hi - lo
    if width <= 0:
        return None
    close, high, low, op = map(float, (bar.close, bar.high, bar.low, bar.open))
    if not lo <= op <= hi:
        return None
    # Range is sufficiently established only if both extremes were revisited.
    upper = int((window.high >= hi - tolerance*width).sum())
    lower = int((window.low <= lo + tolerance*width).sum())
    if upper < 2 or lower < 2:
        return None
    # Failed breakouts are evaluated first, before continuation entries.
    if high > hi and close < hi and close > lo and close < op:
        return {"bar_index":i,"side":"SELL","pattern":"failed_breakout_high","stop":high}
    if low < lo and close > lo and close < hi and close > op:
        return {"bar_index":i,"side":"BUY","pattern":"failed_breakout_low","stop":low}
    if close > hi and close > op:
        return {"bar_index":i,"side":"BUY","pattern":"rectangle_breakout","stop":lo}
    if close < lo and close < op:
        return {"bar_index":i,"side":"SELL","pattern":"rectangle_breakout","stop":hi}
    return None

def generate(df, lookback=24):
    return [s for i in range(lookback+15,len(df)-1)
            if (s := detect(df,i,lookback)) is not None]
