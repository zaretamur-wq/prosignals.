"""Validate user-supplied historical OHLCV data for offline research.

Does not download market data or place orders. CSV timestamps must be UTC.
"""
import argparse
import json
from pathlib import Path
import pandas as pd

def validate_history_csv(path, market, timeframe, min_days=90):
    if market not in ("forex", "crypto"):
        raise ValueError("unsupported market")
    minutes={"5m":5,"1h":60}.get(timeframe)
    if minutes is None:
        raise ValueError("unsupported timeframe")
    if min_days<0:
        raise ValueError("invalid minimum days")
    df=pd.read_csv(path)
    required={"time","open","high","low","close"}
    if market=="crypto":
        required.add("vol")
    if not required.issubset(df.columns):
        raise ValueError("missing columns: "+str(sorted(required-set(df.columns))))
    if len(df)<2:
        raise ValueError("need at least two candles")
    t=pd.to_datetime(df["time"],utc=True,errors="raise")
    if t.isna().any() or t.duplicated().any() or not t.is_monotonic_increasing:
        raise ValueError("invalid, duplicate or unordered timestamps")
    for col in required-{"time"}:
        df[col]=pd.to_numeric(df[col],errors="raise")
        if not df[col].notna().all():
            raise ValueError("missing values in "+col)
    prices=df[["open","high","low","close"]]
    if (prices<=0).any().any():
        raise ValueError("nonpositive prices")
    if ((df["low"]>df[["open","close"]].min(axis=1))|
        (df["high"]<df[["open","close"]].max(axis=1))|
        (df["low"]>df["high"])).any():
        raise ValueError("invalid OHLC")
    if market=="crypto" and (df["vol"]<0).any():
        raise ValueError("negative volume")
    interval=pd.Timedelta(minutes=minutes)
    gaps=t.diff().dropna()
    if (gaps<interval).any() or (gaps%interval!=pd.Timedelta(0)).any():
        raise ValueError("invalid timeframe alignment or duplicate interval")
    missing=int(sum(int(d/interval)-1 for d in gaps if d>interval))
    days=(t.iloc[-1]-t.iloc[0]).total_seconds()/86400
    return {"market":market,"timeframe":timeframe,"candles":len(df),
            "first_utc":t.iloc[0].isoformat(),"last_utc":t.iloc[-1].isoformat(),
            "span_days":round(days,2),"missing_candle_slots":missing,
            "gap_count":int((gaps>interval).sum()),
            "meets_minimum_days":days>=min_days,
            "ready_for_research":days>=min_days and (market=="forex" or missing==0),
            "warning":"Forex market closures require calendar validation. "
                      "Crypto missing intervals must be investigated. "
                      "This is data screening, not strategy validation."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--market",choices=["forex","crypto"],required=True)
    p.add_argument("--timeframe",choices=["5m","1h"],required=True)
    p.add_argument("--min-days",type=int,default=90)
    p.add_argument("--report")
    a=p.parse_args()
    report=validate_history_csv(a.csv,a.market,a.timeframe,a.min_days)
    output=json.dumps(report,indent=2)
    if a.report:
        dest=Path(a.report)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(output+"\n",encoding="utf-8")
    print(output)
    if not report["ready_for_research"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
