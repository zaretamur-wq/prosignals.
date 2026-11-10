"""Research-only, causal M5 signals extracted from two user-supplied video transcripts.

No execution, optimization, win-rate assertion, or broker-order API.
Signals are emitted at CLOSED bar i; execution engines must enter no earlier
than bar i+1 and apply spread, slippage, stops, sizing and daily risk guards.
"""
from zoneinfo import ZoneInfo
import pandas as pd

NY = ZoneInfo("America/New_York")

def _frame(df):
    if not {"time","open","high","low","close"}.issubset(df.columns):
        raise ValueError("M5 UTC time/open/high/low/close columns required")
    t = pd.to_datetime(df["time"], utc=True, errors="raise")
    if t.isna().any() or not t.is_monotonic_increasing or t.duplicated().any():
        raise ValueError("Times must be unique and chronological")
    return t

def twenty_bar_sweep(df, lookback=20, min_depth_atr=0.5, atr_period=14):
    """Video 1: wick crosses PRIOR 20 lows/highs, closes back in, ATR-depth gate."""
    if lookback<2 or atr_period<2 or min_depth_atr<0:
        raise ValueError("Invalid parameters")
    _frame(df)
    tr = pd.concat([(df.high-df.low).abs(),
                    (df.high-df.close.shift()).abs(),
                    (df.low-df.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period, min_periods=atr_period).mean()
    out=[]
    for i in range(max(lookback,atr_period),len(df)-1):
        a=float(atr.iloc[i])
        if not a>0: continue
        prior=df.iloc[i-lookback:i]
        lo=float(prior.low.min()); hi=float(prior.high.max())
        bar=df.iloc[i]
        if bar.low < lo-min_depth_atr*a and bar.close>lo:
            out.append({"bar_index":i,"side":"BUY","stop":float(bar.low),"pattern":"video_20bar_sweep"})
        elif bar.high > hi+min_depth_atr*a and bar.close<hi:
            out.append({"bar_index":i,"side":"SELL","stop":float(bar.high),"pattern":"video_20bar_sweep"})
    return out

def ny_first_four_hour_reentry(df):
    """Video 2: 00:00-04:00 NY-local M5 range, break close, then later close inside.

    Uses explicit NY-local boundaries, including DST. Requires all 48 distinct
    five-minute candles in the NY 00:00-04:00 range; skips incomplete sessions.
    Tracks extremes of the breakout move for a non-lookahead stop.
    """
    t=_frame(df)
    ny=t.dt.tz_convert(NY)
    date=ny.dt.date
    out=[]
    for trading_day in date.unique():
        day_indices=[i for i in range(len(df)) if date.iloc[i]==trading_day]
        first=[i for i in day_indices if ny.iloc[i].hour<4]
        if len(first)!=48: continue
        expected=pd.date_range(ny.iloc[first[0]].normalize(),periods=48,freq="5min")
        if not all(ny.iloc[j]==expected[k] for k,j in enumerate(first)):continue
        hi=float(df.high.iloc[first].max());lo=float(df.low.iloc[first].min())
        # A fresh breakout must be followed by a distinct later closed reentry candle.
        state=0;extreme=None
        for i in day_indices:
            if ny.iloc[i].hour<4 or i>=len(df)-1:continue
            b=df.iloc[i]
            if state==0:
                if b.close>hi: state=-1; extreme=float(b.high)
                elif b.close<lo: state=1; extreme=float(b.low)
            elif state==-1:
                extreme=max(extreme,float(b.high))
                if b.close<hi and b.close>lo:
                    out.append({"bar_index":i,"side":"SELL","stop":extreme,"pattern":"video_ny4h_reentry"})
                    state=0;extreme=None
                elif b.close<lo: state=1;extreme=float(b.low)
            else:
                extreme=min(extreme,float(b.low))
                if b.close>lo and b.close<hi:
                    out.append({"bar_index":i,"side":"BUY","stop":extreme,"pattern":"video_ny4h_reentry"})
                    state=0;extreme=None
                elif b.close>hi: state=-1;extreme=float(b.high)
    return out
