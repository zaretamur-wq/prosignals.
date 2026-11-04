"""Research-only chronological evaluation with auditable source data.

Runs an unchanged baseline independently on each partition; it does not tune
parameters or combine pair-level equity. All fills are hypothetical.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from research_chronological_split import chronological_splits
from research_forex_data_audit import audit_candles
from forex_backtest import backtest

def evaluate(source, symbol, spread_pips=1.5, slippage_pips=0.2,
             embargo=201, initial=100.0, risk_pct=0.03):
    path=Path(source)
    raw=path.read_bytes()
    frame=pd.read_csv(path)
    quality=audit_candles(frame,expected_minutes=5)
    if len(frame)<1500:
        raise ValueError("At least 1500 M5 candles required for meaningful partition warmup")
    # Market closures are flagged, never filled. A report is still allowed,
    # but must not be labeled clean when gaps are present.
    train,validation,test=chronological_splits(frame,embargo=embargo)
    results={}
    for label,partition in (("train",train),("validation",validation),("test",test)):
        if len(partition)<220:
            raise ValueError(f"{label} too short for baseline warmup")
        r=backtest(partition,symbol=symbol,initial=initial,risk_pct=risk_pct,
                   spread_pips=spread_pips,slippage_pips=slippage_pips)
        results[label]={k:v for k,v in r.items() if k!="trade_log"}
        results[label]["trade_log"]=r["trade_log"]
    return {"symbol":symbol,"source_sha256":hashlib.sha256(raw).hexdigest(),
            "source_file":str(path),"quality":quality,
            "split":"60/20/20 chronological; embargo after first and second boundary",
            "embargo_bars":embargo,"assumed_spread_pips":spread_pips,
            "assumed_slippage_pips":slippage_pips,
            "results":results,
            "status":"research_only_not_broker_verified",
            "limitations":["No XM-confirmed spread, swap, commission, leverage or margin",
                           "Only EURUSD and GBPUSD baseline supported",
                           "Data quality may fail for market closures; review gap timestamps",
                           "Independent partition equity resets; no carryover positions",
                           "No parameter tuning or broker execution",
                           "Test is not untouched if models were chosen after seeing it"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--symbol",choices=["EURUSD","GBPUSD"],required=True)
    p.add_argument("--spread-pips",type=float,default=1.5)
    p.add_argument("--slippage-pips",type=float,default=0.2)
    p.add_argument("--embargo",type=int,default=201)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=evaluate(a.csv,a.symbol,a.spread_pips,a.slippage_pips,a.embargo)
    output=Path(a.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
    for key,value in report["results"].items():
        print(key, "trades=",value["trades"],"win_rate_pct=",value["win_rate_pct"],
              "final_usd=",value["final_usd"])
