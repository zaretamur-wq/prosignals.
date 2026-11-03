"""XM-style minimum-lot feasibility screen for research entry models.
This does not model margin, spreads, swaps or live execution.
"""
import argparse
import json
from pathlib import Path
from historical_replay import load_csv
from research_entry_candidates import generate

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    df=load_csv(a.csv)
    # USDJPY stop risk is denominated in JPY; convert approximately at entry.
    # GOLD uses 100 oz per lot, other FX 100,000 base units per lot.
    gold=a.symbol=="GOLD"
    contract=100 if gold else 100000
    lot=.01
    budget=.50
    result={}
    for method in ("pullback","breakout","range"):
        signals=generate(df,method)
        eligible=0
        risk_values=[]
        for s in signals:
            entry=float(df.iloc[s["bar_index"]+1]["open"])
            distance=abs(entry-s["stop"])
            quote_risk=distance*contract*lot
            usd_risk=quote_risk/entry if a.symbol=="USDJPY" else quote_risk
            risk_values.append(usd_risk)
            if usd_risk<=budget: eligible+=1
        result[method]={"candidate_signals":len(signals),
                        "within_50_cent_stop_risk":eligible,
                        "minimum_lot":lot,
                        "median_minimum_lot_stop_risk_usd":round(sorted(risk_values)[len(risk_values)//2],3) if risk_values else None}
    report={"symbol":a.symbol,"starting_capital_usd":100,
            "risk_budget_usd":budget,"entry_model_screen":result,
            "warning":"Minimum-lot stop-distance feasibility ONLY; excludes floating spread, commission, slippage, margin and swap. Eligible does NOT mean executable or profitable. XM account-specific specs must be verified."}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
