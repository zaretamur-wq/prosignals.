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
import pandas as pd

def compare(df, symbol, spread_pips, risk_fraction=0.03, rr=2.0, leverage=100):
    split=int(len(df)*0.7)
    if split<300 or len(df)-split<100:
        raise ValueError("Need at least 1000 candles for comparison")
    results={}
    # Closed-candle trend and stop-distance quality filter; no lookahead.
    close=df["close"]
    ema20=close.ewm(span=20,adjust=False).mean()
    ema80=close.ewm(span=80,adjust=False).mean()
    tr=pd.concat([df.high-df.low,(df.high-close.shift()).abs(),
                  (df.low-close.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14).mean()
    raw_patterns=pattern_generate(df)
    filtered=[]
    for s in raw_patterns:
        i=s["bar_index"]
        if i<100 or pd.isna(atr.iloc[i]) or atr.iloc[i]<=0: continue
        direction=1 if s["side"]=="BUY" else -1
        trend=direction*(ema20.iloc[i]-ema80.iloc[i])>0
        slope=direction*(ema80.iloc[i]-ema80.iloc[i-5])>0
        stop_distance=direction*(float(df.close.iloc[i])-float(s["stop"]))
        # Stop not so tight that assumed spread dominates, nor too wide.
        if trend and slope and 0.8*atr.iloc[i]<=stop_distance<=2.5*atr.iloc[i]:
            filtered.append(s)
    # Independent M5 candidates: confirmed breakout retest and RSI sweep.
    # At index i only bars <= i are read; entry is simulated next bar.
    rsi_delta=close.diff()
    up=rsi_delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    down=(-rsi_delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=100-100/(1+up/down.replace(0,float("nan")))
    adx_tr=tr.ewm(alpha=1/14,adjust=False).mean()
    m5_retest=[]
    m5_sweep=[]
    for i in range(110,len(df)-1):
        a=float(atr.iloc[i])
        if not a>0:continue
        previous=df.iloc[i-21:i-1]
        hi=float(previous.high.max())
        lo=float(previous.low.min())
        b=df.iloc[i]; p=df.iloc[i-1]
        # Prior bar breaks old range; current completed bar retests.
        if p.close>hi+0.12*a and b.low<=hi+0.15*a and b.close>hi and b.close>b.open and ema20.iloc[i]>ema80.iloc[i]:
            m5_retest.append({"bar_index":i,"side":"BUY","stop":min(float(b.low),hi-0.5*a),"pattern":"retest"})
        elif p.close<lo-0.12*a and b.high>=lo-0.15*a and b.close<lo and b.close<b.open and ema20.iloc[i]<ema80.iloc[i]:
            m5_retest.append({"bar_index":i,"side":"SELL","stop":max(float(b.high),lo+0.5*a),"pattern":"retest"})
        if b.low<lo-0.1*a and b.close>lo and b.close>b.open and rsi.iloc[i]<48:
            m5_sweep.append({"bar_index":i,"side":"BUY","stop":float(b.low)-0.1*a,"pattern":"sweep"})
        elif b.high>hi+0.1*a and b.close<hi and b.close<b.open and rsi.iloc[i]>52:
            m5_sweep.append({"bar_index":i,"side":"SELL","stop":float(b.high)+0.1*a,"pattern":"sweep"})
    methods={
        "original_pullback":original_generate(df,"pullback"),
        "original_breakout":original_generate(df,"breakout"),
        "original_range":original_generate(df,"range"),
        "chart_patterns_all":raw_patterns,
        "chart_patterns_trend_filtered":filtered,
        "m5_breakout_retest":m5_retest,
        "m5_rsi_liquidity_sweep":m5_sweep,
    }
    # Exit-structure sweep: identical entries, compare 0.75R, 1R, 1.5R and 2R.
    # Training metrics guide selection; holdout is reported separately.
    for name, signals in methods.items():
        results[name]={
            "signals":len(signals),
            "train":run(df,symbol,signals,0,split,risk_fraction,rr,spread_pips,leverage),
            "holdout":run(df,symbol,signals,split,len(df),risk_fraction,rr,spread_pips,leverage),
        }
    for name in ("m5_rsi_liquidity_sweep","chart_patterns_all","m5_breakout_retest"):
        signals=methods[name]
        for target_r in (0.75,1.0,1.5):
            results[name+"_target_"+str(target_r)+"R"]={
                "signals":len(signals),
                "train":run(df,symbol,signals,0,split,risk_fraction,target_r,spread_pips,leverage),
                "holdout":run(df,symbol,signals,split,len(df),risk_fraction,target_r,spread_pips,leverage),
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
    path.write_text(json.dumps(result,indent=2)+chr(10))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
