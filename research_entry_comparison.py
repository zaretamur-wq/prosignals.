"""Compare frozen alternative entry models on a chronological holdout."""
import argparse
import json
from pathlib import Path
from historical_replay import load_csv
from research_entry_candidates import generate
from trade_lifecycle import backtest_lifecycle
from shared_risk import InstrumentSpec, RiskPolicy

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    df=load_csv(args.csv,True)
    bars=[{"time":t.isoformat(),**{k:float(v) for k,v in row.items()}} for t,row in df.iterrows()]
    split=int(len(bars)*0.7)
    results={}
    for method in ("pullback","breakout","range"):
        all_signals=generate(df,method)
        parts={}
        for label,start,end in (("train",0,split),("holdout",split,len(bars))):
            signals=[{**s,"bar_index":s["bar_index"]-start} for s in all_signals
                     if start<=s["bar_index"]<end-1]
            trades,equity=backtest_lifecycle(
                bars[start:end],signals,100,
                InstrumentSpec(args.symbol,0.000001,0.000001,1),RiskPolicy(),
                expire_minutes=240,slippage_fraction=0.0005,fee_rate=0.001)
            finished=[t for t in trades if t.outcome!="END_OF_TEST"]
            wins=sum(t.pnl>0 for t in finished)
            profit=sum(max(t.pnl,0) for t in finished)
            loss=sum(max(-t.pnl,0) for t in finished)
            parts[label]={"signals":len(signals),"trades":len(finished),
                          "win_rate":round(wins/len(finished),4) if finished else None,
                          "net_pnl":round(equity-100,4),
                          "profit_factor":round(profit/loss,4) if loss else None}
        results[method]=parts
    output={"symbol":args.symbol,"capital":100,"results":results,
            "warning":"Research-only historical OHLC; 70/30 split, no live orders. Fee 0.1% each side, slippage 0.05% each fill. Repeated model inspection can contaminate holdout."}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))
if __name__=="__main__":main()
