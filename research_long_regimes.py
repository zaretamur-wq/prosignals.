"""Long-history market-regime diagnostic; NOT a trading strategy backtest.

Uses close-to-close past returns only for regime classification, and measures
subsequent returns separately. Never optimizes parameters on the holdout.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

def analyze(df, lookback=60, horizon=5, holdout_fraction=0.3):
    if not 0<holdout_fraction<1 or lookback<5 or horizon<1:
        raise ValueError("invalid research parameters")
    if len(df)<lookback+horizon+30:
        raise ValueError("insufficient candles")
    time=pd.to_datetime(df["time"],utc=True)
    if time.isna().any() or time.duplicated().any() or not time.is_monotonic_increasing:
        raise ValueError("invalid timestamps")
    close=pd.to_numeric(df["close"],errors="raise").to_numpy(dtype=float)
    if not np.isfinite(close).all() or (close<=0).any():
        raise ValueError("invalid prices")
    momentum=pd.Series(close).pct_change(lookback).to_numpy()
    # Forward returns are used for evaluation only, NEVER for regime labels.
    forward=np.full(len(close),np.nan)
    forward[:-horizon]=close[horizon:]/close[:-horizon]-1
    valid=np.arange(lookback,len(close)-horizon)
    split=int(len(close)*(1-holdout_fraction))
    if split<=lookback or split>=len(close)-horizon:
        raise ValueError("insufficient chronological train/holdout")
    results={}
    for label,indices in (("development",valid[valid<split]),
                          ("holdout",valid[valid>=split])):
        groups={}
        for regime,mask in (("up",momentum[indices]>0.01),
                            ("down",momentum[indices]<-0.01),
                            ("range",np.abs(momentum[indices])<=0.01)):
            v=forward[indices[mask]]
            groups[regime]={"observations":int(len(v)),
                            "mean_forward_return_pct":round(float(v.mean()*100),4) if len(v) else None,
                            "positive_forward_fraction":round(float((v>0).mean()),4) if len(v) else None}
        results[label]={"start_utc":str(time.iloc[indices[0]]),
                        "end_utc":str(time.iloc[indices[-1]]),
                        "regimes":groups}
    return {"bars":len(df),"lookback_bars":lookback,"forward_horizon_bars":horizon,
            "split_index":split,"segments":results,
            "warning":"Descriptive market regime study only, not strategy P&L. "
                      "Overlapping forward returns are correlated; no statistical "
                      "independence or future profitability is implied."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--lookback",type=int,default=60)
    p.add_argument("--horizon",type=int,default=5)
    a=p.parse_args()
    result=analyze(pd.read_csv(a.csv),a.lookback,a.horizon)
    dest=Path(a.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
