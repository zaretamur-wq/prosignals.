"""Compare original entry candidates against causal chart patterns on the SAME candles.
Research only. Prints measured train/holdout results; never sends orders.
Example:
 python compare_original_patterns.py --csv EURUSD_5m.csv --symbol EURUSD --output comparison.json
"""
import argparse
import json
from pathlib import Path
from historical_replay import load_csv
from research_entry_candidates import generate as original_generate
from forex_chart_patterns import generate as pattern_generate
from research_xm_standard_forex import run, PIP, SPREAD_PIPS

def compare(df, symbol, spread_pips, risk_fraction=0.03, rr=2.0, leverage=100):
    split=int(len(df)*0.7)
    if split<300 or len(df)-split<100:
        raise ValueError("Need at least 1000 candles for comparison")
    results={}
    methods={
        "original_pullback":original_generate(df,"pullback"),
        "original_breakout":original_generate(df,"breakout"),
        "original_range":original_generate(df,"range"),
        "chart_patterns_all":pattern_generate(df),
    }
    for name, signals in methods.items():
        results[name]={
            "signals":len(signals),
            "train":run(df,symbol,signals,0,split,risk_fraction,rr,spread_pips,leverage),
            "holdout":run(df,symbol,signals,split,len(df),risk_fraction,rr,spread_pips,leverage),
        }
    return {"symbol":symbol,"candles":len(df),"split_index":split,
            "assumed_spread_pips":spread_pips,"risk_fraction":risk_fraction,
            "rr":rr,"results":results,
            "limitations":"No real broker quotes, commissions, swaps or news; H1 research engine reused; not an M5 execution validation. No live orders."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--symbol",choices=list(PIP),required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--spread-pips",type=float)
    p.add_argument("--risk",type=float,default=0.03)
    p.add_argument("--rr",type=float,default=2.0)
    p.add_argument("--leverage",type=float,default=100)
    a=p.parse_args()
    if not 0<a.risk<=0.03 or a.rr<=0 or a.leverage<=0:
        p.error("invalid risk, rr or leverage")
    df=load_csv(a.csv)
    result=compare(df,a.symbol,SPREAD_PIPS[a.symbol] if a.spread_pips is None else a.spread_pips,a.risk,a.rr,a.leverage)
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
