"""Compare fixed video-derived EURUSD M5 candidates on chronological train/holdout.

Research-only; no orders. NOT a faithful broker-tick backtest. Signals are
generated on completed M5 candles and filled at the following candle open.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from research_video_candidates import twenty_bar_sweep, ny_first_four_hour_reentry
from research_xm_standard_forex import run

def evaluate(df, spread_pips=1.8, risk_fraction=0.01, leverage=100):
    if not 0 < risk_fraction <= 0.03 or spread_pips < 0 or leverage <= 0:
        raise ValueError("Invalid research costs/risk/leverage")
    required={"time","open","high","low","close"}
    if not required.issubset(df.columns):
        raise ValueError("Requires time/open/high/low/close")
    df=df.copy().reset_index(drop=True)
    t=pd.to_datetime(df.time,utc=True,errors="raise")
    if t.isna().any() or t.duplicated().any() or not t.is_monotonic_increasing:
        raise ValueError("Time must be unique and chronological")
    if len(df)<1000:
        raise ValueError("At least 1000 M5 bars required")
    for k in ("open","high","low","close"):
        df[k]=pd.to_numeric(df[k],errors="raise")
    if df[["open","high","low","close"]].isna().any().any():
        raise ValueError("Missing OHLC")
    # Gap/density guard; research NY range generator skips incomplete days itself.
    if (df.high<df[["open","low","close"]].max(axis=1)).any() or (df.low>df[["open","close"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC")
    cut=int(len(df)*0.7)
    candidates={"video_20bar_sweep_half_atr":twenty_bar_sweep(df),
                "video_ny_first_4h_reentry":ny_first_four_hour_reentry(df)}
    out={"symbol":"EURUSD","timeframe":"M5","candles":len(df),
         "split_index":cut,"assumed_spread_pips":spread_pips,
         "risk_fraction":risk_fraction,"leverage":leverage,
         "strategies":{},"limitations":[
           "No real-tick intra-bar sequencing; stops checked before targets on ambiguous candles",
           "Fixed assumed spreads and simplified margin/lot model",
           "No slippage, commissions, swaps, news or daily realized-loss guard",
           "Research engine originally built for H1; M5 results exploratory only",
           "No shared multi-pair capital or portfolio backtest",
           "Train/holdout split is chronological but lacks embargo; future independent testing required"] }
    for name,signals in candidates.items():
        result={"signal_count":len(signals)}
        for rr in (1.0,2.0):
            result[f"{rr:g}R"]={
                "train":run(df,"EURUSD",signals,0,cut,risk_fraction,rr,spread_pips,leverage),
                "holdout":run(df,"EURUSD",signals,cut,len(df),risk_fraction,rr,spread_pips,leverage)}
        out["strategies"][name]=result
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--spread-pips",type=float,default=1.8)
    p.add_argument("--risk",type=float,default=0.01)
    p.add_argument("--leverage",type=float,default=100)
    a=p.parse_args()
    report=evaluate(pd.read_csv(a.csv),a.spread_pips,a.risk,a.leverage)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
