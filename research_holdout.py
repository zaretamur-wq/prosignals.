"""Chronological holdout evaluation for paper-only research.

Never select a filter using the holdout results. Compare fixed candidates
on the same signal-generation history, split by SIGNAL candle index.
Capital is reset at each partition; open trades are not carried over.
"""
from trade_lifecycle import backtest_lifecycle
from shared_backtest import run_backtest
from shared_risk import RiskPolicy
from research_regimes import regimes,regime_filter


def compare_holdout(bars, signals, market, instrument, capital,
                    split_fraction=.7, slippage=0, fee_rate=0,
                    expire_minutes=240):
    if not 0.5 <= split_fraction <= 0.9:
        raise ValueError("split_fraction must be 0.5..0.9")
    if market not in ("crypto","forex"):
        raise ValueError("unsupported market")
    split = int(len(bars)*split_fraction)
    if split < 2 or len(bars)-split < 2:
        raise ValueError("insufficient bars")
    regime_data = regimes(bars)
    output = {"split_index":split,"train_bars":split,
              "holdout_bars":len(bars)-split,"train":{},"holdout":{}}
    for part,start,end in (("train",0,split),("holdout",split,len(bars))):
        sample_bars=bars[start:end]
        for mode in ("all","trend","trend_and_volatility"):
            selected=regime_filter(signals,regime_data,mode)
            selected=[{**s,"bar_index":s["bar_index"]-start}
                      for s in selected if start<=s["bar_index"]<end-1]
            if market=="crypto":
                trades,equity=backtest_lifecycle(
                    sample_bars,selected,capital,instrument,RiskPolicy(),
                    expire_minutes=expire_minutes,
                    slippage_fraction=slippage,fee_rate=fee_rate)
            else:
                trades,equity=run_backtest(
                    sample_bars,selected,capital,instrument,RiskPolicy(),slippage)
            completed=[t for t in trades if t.outcome!="END_OF_TEST"]
            profit=sum(t.pnl for t in completed if t.pnl>0)
            loss=-sum(t.pnl for t in completed if t.pnl<0)
            output[part][mode]={
                "signals":len(selected),
                "completed_trades":len(completed),
                "win_rate":sum(t.pnl>0 for t in completed)/len(completed)
                           if completed else None,
                "net_pnl":equity-capital,
                "profit_factor":profit/loss if loss else None,
            }
    output["warning"]=(
        "Research-only chronological 70/30 split. Signal-generation warmup "
        "and historical non-OHLC filter omissions remain; holdout is only "
        "untouched if candidate parameters were fixed BEFORE inspecting it. "
        "Do not tune on the holdout.")
    return output
