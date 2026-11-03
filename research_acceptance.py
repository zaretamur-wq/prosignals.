"""Conservative strategy acceptance checks for offline research.

This module does not optimize a strategy, place orders, or claim profitability.
All inputs must come from completed out-of-sample trades after trading costs.
"""
import argparse
import json
import math
from pathlib import Path

def assess_trades(net_returns, min_trades=100, max_drawdown_fraction=0.15,
                  min_profit_factor=1.2):
    if min_trades<1 or not 0<max_drawdown_fraction<1 or min_profit_factor<=1:
        raise ValueError("invalid acceptance thresholds")
    returns=[float(x) for x in net_returns]
    if any(not math.isfinite(x) or x<=-1 for x in returns):
        raise ValueError("returns must be finite fractions greater than -100%")
    equity=1.0
    peak=1.0
    drawdown=0.0
    for r in returns:
        equity*=1+r
        peak=max(peak,equity)
        drawdown=max(drawdown,1-equity/peak)
    wins=sum(x>0 for x in returns)
    losses=sum(x<0 for x in returns)
    gains=sum(x for x in returns if x>0)
    lost=-sum(x for x in returns if x<0)
    pf=gains/lost if lost else (None if gains==0 else float("inf"))
    total_return=equity-1
    checks={"enough_trades":len(returns)>=min_trades,
            "positive_net_return":total_return>0,
            "drawdown_within_limit":drawdown<=max_drawdown_fraction,
            "profit_factor_above_minimum":pf is not None and pf>=min_profit_factor,
            "both_winners_and_losers":wins>0 and losses>0}
    return {"completed_trades":len(returns),
            "win_rate":round(wins/len(returns),4) if returns else None,
            "compounded_net_return_fraction":round(total_return,6),
            "maximum_drawdown_fraction":round(drawdown,6),
            "profit_factor":round(pf,4) if pf is not None and math.isfinite(pf) else None,
            "checks":checks,
            "research_gate_passed":all(checks.values()),
            "warning":"Passing this research gate does not authorize live trading. "
                      "Requires verified out-of-sample, cost-inclusive returns; "
                      "demo execution and broker-specific risk checks remain mandatory."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--returns-json",required=True,
                   help="JSON array of per-trade net account returns as fractions")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    data=json.loads(Path(a.returns_json).read_text())
    if not isinstance(data,list):
        raise ValueError("expected JSON array")
    report=assess_trades(data)
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
