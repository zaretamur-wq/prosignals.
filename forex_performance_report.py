"""Evaluate completed research trades without interpreting signal scores as probabilities."""
from math import isfinite

def summarize(trade_log, initial_usd=100.0):
    if not isfinite(initial_usd) or initial_usd<=0:
        raise ValueError("initial_usd must be positive and finite")
    pnls=[]
    for trade in trade_log:
        value=float(trade["pnl_usd"])
        if not isfinite(value):
            raise ValueError("nonfinite trade P&L")
        pnls.append(value)
    wins=[v for v in pnls if v>0]
    losses=[v for v in pnls if v<0]
    gross_profit=sum(wins)
    gross_loss=-sum(losses)
    equity=initial_usd
    peak=initial_usd
    drawdown=0.0
    for pnl in pnls:
        equity+=pnl
        peak=max(peak,equity)
        drawdown=max(drawdown,(peak-equity)/peak)
    return {
        "completed_trades":len(pnls),
        "wins":len(wins),
        "losses":len(losses),
        "breakeven":len(pnls)-len(wins)-len(losses),
        "win_rate_pct":round(100*len(wins)/len(pnls),2) if pnls else None,
        "profit_factor":round(gross_profit/gross_loss,4) if gross_loss else None,
        "profit_factor_note":"undefined without losses" if not gross_loss else None,
        "net_pnl_usd":round(sum(pnls),2),
        "max_closed_trade_drawdown_pct":round(100*drawdown,2),
        "average_pnl_per_trade_usd":round(sum(pnls)/len(pnls),4) if pnls else None,
        "warning":"Closed-trade equity drawdown excludes intratrade floating drawdown; values depend on simulator assumptions."
    }
