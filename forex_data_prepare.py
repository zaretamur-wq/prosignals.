"""Validate and normalize third-party EURUSD M5 CSV data for ProSignals.

Accepts common Dukascopy CSV columns (timestamp/open/high/low/close)
and MT5 columns (<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>).
Output is UTC OHLC compatible with forex_backtest.py.
Timezone of a timestamp WITHOUT an offset must be supplied explicitly.
"""
import argparse
import pandas as pd

def normalize_csv(path, timezone="UTC"):
    d = pd.read_csv(path, sep=None, engine="python")
    d.columns = [str(c).strip().lower().strip("<>") for c in d.columns]
    if "time" not in d and "timestamp" in d:
        d = d.rename(columns={"timestamp":"time"})
    if "date" in d and "time" in d:
        d["time"] = d["date"].astype(str) + " " + d["time"].astype(str)
    elif "date" in d:
        d = d.rename(columns={"date":"time"})
    needed = ["time","open","high","low","close"]
    missing = set(needed)-set(d.columns)
    if missing:
        raise ValueError(f"Missing columns {missing}; got {list(d.columns)}")
    d = d[needed].copy()
    ts = pd.to_datetime(d["time"], errors="raise", utc=False, format="mixed")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    d["time"] = ts.dt.tz_convert("UTC")
    for col in needed[1:]:
        d[col] = pd.to_numeric(d[col], errors="raise")
    d = d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    if d[needed[1:]].isna().any().any() or (d[needed[1:]] <= 0).any().any():
        raise ValueError("Invalid or missing OHLC")
    if ((d.high < d[["open","close","low"]].max(axis=1)) |
        (d.low > d[["open","close","high"]].min(axis=1))).any():
        raise ValueError("Inconsistent OHLC")
    delta = d.time.diff().dropna()
    # Weekend/holiday gaps are expected; reject bars closer than five minutes.
    if (delta < pd.Timedelta(minutes=5)).any():
        raise ValueError("Duplicate/overlapping bars or unexpected timeframe")
    regular = (delta == pd.Timedelta(minutes=5)).sum()
    if regular == 0:
        raise ValueError("No consecutive M5 candles detected")
    return d, {"bars":len(d), "start":str(d.time.iloc[0]),"end":str(d.time.iloc[-1]),
               "consecutive_m5_fraction":round(float(regular/len(delta)),4)}

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("output_csv")
    p.add_argument("--timezone",default="UTC",help="Timezone for naive timestamps, e.g. UTC")
    args=p.parse_args()
    d, report=normalize_csv(args.input_csv,args.timezone)
    d.to_csv(args.output_csv,index=False)
    print(report)
