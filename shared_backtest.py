"""Conservative OHLC backtesting foundation for Forex, gold and crypto.

Signals are known after candle close; trade at next open. If stop and target
both occur within one OHLC bar, assume stop first. Not a tick-level simulator.
No live orders. Prices and value must be normalized to account currency.
"""
from dataclasses import dataclass
from math import isfinite
from shared_risk import InstrumentSpec, RiskPolicy, size_position

@dataclass
class Trade:
    side: str
    entry_time: object
    exit_time: object
    entry: float
    exit: float
    quantity: float
    pnl: float
    outcome: str

def run_backtest(bars, signals, initial_equity, spec: InstrumentSpec,
                 policy=RiskPolicy(), slippage_fraction=0.0, position_sizer=None):
    """Return (trades, final_equity); only one position at a time.

    bars: list of {time, open, high, low, close}
    signals: list of {bar_index, side, stop, target}; signal at close.
    Pricing is simplified: no spread, margin, swaps or partial TP yet.
    """
    if not isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("invalid starting capital")
    if not isfinite(slippage_fraction) or not 0 <= slippage_fraction < 1:
        raise ValueError("invalid slippage")
    by_index = {}
    for s in signals:
        idx = s["bar_index"]
        if not isinstance(idx, int) or idx < 0 or idx >= len(bars)-1:
            raise ValueError("signal must have a next candle")
        if idx in by_index:
            raise ValueError("multiple signals for one bar not supported")
        by_index[idx] = s
    sizing = position_sizer if position_sizer is not None else size_position
    equity, position, pending, trades = float(initial_equity), None, None, []
    day, daily_pnl = None, 0.0
    for i, b in enumerate(bars):
        op, hi, lo, cl = (float(b[k]) for k in ("open","high","low","close"))
        if (not all(isfinite(x) and x > 0 for x in (op,hi,lo,cl))
                or not lo <= min(op,cl) <= max(op,cl) <= hi):
            raise ValueError("invalid OHLC candle")
        current_day = str(b["time"])[:10]
        if current_day != day:
            day, daily_pnl = current_day, 0.0
        # The signal was generated at the PREVIOUS candle close.
        if pending is not None and position is None:
            s, pending = pending, None
            buy = s["side"] == "BUY"
            if s["side"] not in ("BUY","SELL"):
                raise ValueError("invalid direction")
            entry = op * (1+slippage_fraction if buy else 1-slippage_fraction)
            stop, target = float(s["stop"]), float(s["target"])
            if not all(isfinite(v) and v>0 for v in (stop,target)):
                raise ValueError("invalid exit levels")
            if (buy and stop < entry < target) or (not buy and target < entry < stop):
                qty, _ = sizing(equity, entry, stop, spec, policy,
                                       realized_daily_pnl=daily_pnl)
                if qty > 0:
                    position = dict(side=s["side"], entry=entry, stop=stop,
                                    target=target, quantity=qty,time=b["time"])
        if position is not None:
            p = position
            buy = p["side"] == "BUY"
            hit_stop = lo <= p["stop"] if buy else hi >= p["stop"]
            hit_target = hi >= p["target"] if buy else lo <= p["target"]
            if hit_stop or hit_target:
                # Conservative same-candle ambiguity resolution.
                if hit_stop:
                    raw_exit = min(op,p["stop"]) if buy else max(op,p["stop"])
                    outcome = "STOP"
                else:
                    raw_exit, outcome = p["target"], "TARGET"
                exit_price = raw_exit*(1-slippage_fraction if buy else 1+slippage_fraction)
                pnl = ((exit_price-p["entry"])*(1 if buy else -1)
                       *p["quantity"]*spec.price_value_per_unit
                       -2*p["quantity"]*spec.commission_per_unit_per_side)
                equity += pnl
                daily_pnl += pnl
                trades.append(Trade(p["side"],p["time"],b["time"],p["entry"],
                                    exit_price,p["quantity"],pnl,outcome))
                position = None
        if position is None and i in by_index:
            pending = by_index[i]
    if position is not None:
        p = position
        buy = p["side"] == "BUY"
        final_close = float(bars[-1]["close"])
        exit_price = final_close*(1-slippage_fraction if buy else 1+slippage_fraction)
        pnl = ((exit_price-p["entry"])*(1 if buy else -1)
               *p["quantity"]*spec.price_value_per_unit
               -2*p["quantity"]*spec.commission_per_unit_per_side)
        equity += pnl
        trades.append(Trade(p["side"],p["time"],bars[-1]["time"],p["entry"],
                            exit_price,p["quantity"],pnl,"END_OF_TEST"))
    return trades, equity
