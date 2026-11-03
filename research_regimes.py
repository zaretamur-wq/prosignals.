"""Point-in-time, research-only OHLC trend and volatility regimes.

A candidate at index i can only see candles <= i. The regime is
independent of future trade outcomes; no fitting to target labels.
"""
import math

def regimes(bars, lookback=48, trend_threshold=0.006, volatility_floor=0.002):
    if lookback < 3 or trend_threshold < 0 or volatility_floor < 0:
        raise ValueError("invalid regime parameters")
    out = []
    closes = []
    for bar in bars:
        close = float(bar["close"])
        if not math.isfinite(close) or close <= 0:
            raise ValueError("invalid closing price")
        closes.append(close)
        if len(closes) <= lookback:
            out.append(None)
            continue
        old = closes[-lookback-1]
        change = close/old - 1
        # Only preceding and current closes; no next-bar leakage.
        returns = [math.log(closes[j]/closes[j-1])
                   for j in range(len(closes)-lookback,len(closes))]
        rms = math.sqrt(sum(v*v for v in returns)/len(returns))
        direction = ("UP" if change > trend_threshold else
                     "DOWN" if change < -trend_threshold else "RANGE")
        out.append({"trend":direction,"change":change,"volatility":rms,
                    "volatile":rms >= volatility_floor})
    return out

def regime_filter(signals, regimes_by_bar, mode):
    if mode not in ("all","trend","trend_and_volatility","range_only","countertrend"):
        raise ValueError("unsupported regime mode")
    if mode == "all":
        return list(signals)
    chosen=[]
    for s in signals:
        r=regimes_by_bar[s["bar_index"]]
        if r is None:
            continue
        if mode == "countertrend":
            if (s["side"]=="BUY" and r["trend"]=="DOWN") or (s["side"]=="SELL" and r["trend"]=="UP"):
                chosen.append(s)
            continue
        if mode == "range_only":
            if r["trend"] == "RANGE":
                chosen.append(s)
            continue
        direction_ok=(s["side"]=="BUY" and r["trend"]=="UP") or (
            s["side"]=="SELL" and r["trend"]=="DOWN")
        if direction_ok and (mode=="trend" or r["volatile"]):
            chosen.append(s)
    return chosen
