"""Preflight checks for offline Forex OHLC research; no order execution."""
import argparse
import json
import pandas as pd
import numpy as np

def audit_candles(frame, expected_minutes=5):
    if expected_minutes <= 0:
        raise ValueError("expected_minutes must be positive")
    required = {"time","open","high","low","close"}
    if not required.issubset(frame.columns):
        raise ValueError("missing OHLC/time columns")
    times = pd.to_datetime(frame["time"],utc=True,errors="raise")
    if times.isna().any() or times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError("timestamps must be strictly increasing and unique")
    prices=frame[["open","high","low","close"]].apply(pd.to_numeric,errors="raise")
    values=prices.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values<=0).any():
        raise ValueError("prices must be finite and positive")
    if ((prices.high < prices[["open","low","close"]].max(axis=1)) |
        (prices.low > prices[["open","high","close"]].min(axis=1))).any():
        raise ValueError("invalid OHLC geometry")
    gaps=times.diff().dropna().dt.total_seconds()/60
    # Weekend and market closure gaps are reported, not silently filled.
    unexpected=gaps[gaps!=expected_minutes]
    return {"rows":len(frame),"first_utc":str(times.iloc[0]) if len(times) else None,
            "last_utc":str(times.iloc[-1]) if len(times) else None,
            "expected_interval_minutes":expected_minutes,
            "nonstandard_interval_count":int(len(unexpected)),
            "largest_gap_minutes":float(gaps.max()) if len(gaps) else None,
            "data_quality_pass":bool(len(frame)>=220 and len(unexpected)==0),
            "warning":"Market closure gaps require documented review; no missing bars are fabricated."}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--minutes",type=int,default=5)
    args=parser.parse_args()
    print(json.dumps(audit_candles(pd.read_csv(args.csv),args.minutes),indent=2))
