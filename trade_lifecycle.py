"""Research-only TP1 -> breakeven -> TP2 trade simulation.

One position at a time. Entries occur at the next bar open, never on the
signal candle. Unresolved same-candle paths are handled pessimistically.
This is NOT an exchange simulator and cannot send orders.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from shared_risk import size_position, InstrumentSpec, RiskPolicy

@dataclass
class LifecycleTrade:
    side: str
    entry_time: str
    exit_time: str
    entry: float
    quantity: float
    pnl: float
    outcome: str
    tp1_hit: bool
    exit_price: float

def backtest_lifecycle(bars, signals, capital, spec: InstrumentSpec,
                       policy=RiskPolicy(), tp1_fraction=0.5,
                       expire_minutes=240, slippage_fraction=0.0):
    """Signals: {bar_index,side,stop,tp1,tp2}. Returns trades, equity.

    Assumes TP1 fills half, remainder stop moves to entry from NEXT candle.
    Stop wins ties. If TP1 and original stop both touch, stop wins. If TP1
    and TP2 touch, record TP1 only and delay TP2 until the next candle.
    Exit at expiry close, not an invented historical tick price.
    Fees charged per entry and exit portion. No spread/margin modeled.
    """
    if not isfinite(capital) or capital <= 0 or not 0 < tp1_fraction < 1:
        raise ValueError("invalid capital or TP1 fraction")
    if not isfinite(slippage_fraction) or not 0 <= slippage_fraction < 1:
        raise ValueError("invalid slippage")
    if expire_minutes <= 0: raise ValueError("invalid expiry")
    indexed = {}
    for s in signals:
        idx = s["bar_index"]
        if not isinstance(idx, int) or not 0 <= idx < len(bars)-1:
            raise ValueError("invalid signal index")
        if idx in indexed: raise ValueError("duplicate signal on candle")
        indexed[idx] = s
    def time_of(b):
        ts = str(b["time"]).replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None: raise ValueError("UTC timestamp required")
        return dt.astimezone(timezone.utc)
    equity = float(capital)
    records = []
    active = None
    pending = None
    day = None
    daily_pnl = 0.0
    for i, b in enumerate(bars):
        current_time = time_of(b)
        current_day = current_time.date()
        if day != current_day:
            day, daily_pnl = current_day, 0.0
        op, hi, lo, cl = (float(b[k]) for k in ("open","high","low","close"))
        if not all(isfinite(v) and v > 0 for v in (op, hi, lo, cl)):
            raise ValueError("invalid candle")
        if not lo <= min(op, cl) <= max(op, cl) <= hi:
            raise ValueError("inconsistent candle")
        if active is None and pending is not None:
            s = pending
            pending = None
            side = s["side"]
            if side not in ("BUY","SELL"): raise ValueError("invalid side")
            sign = 1 if side == "BUY" else -1
            entry = op * (1 + sign*slippage_fraction)
            stop, tp1, tp2 = (float(s[k]) for k in ("stop","tp1","tp2"))
            if not all(isfinite(v) and v > 0 for v in (stop,tp1,tp2)):
                raise ValueError("invalid target")
            if (sign==1 and stop < entry < tp1 < tp2) or (sign==-1 and tp2 < tp1 < entry < stop):
                qty, _ = size_position(equity,entry,stop,spec,policy,
                                       realized_daily_pnl=daily_pnl)
                if qty > 0:
                    active = dict(side=side,sign=sign,entry=entry,stop=stop,
                                  tp1=tp1,tp2=tp2,qty=qty,started=current_time,
                                  tp1_hit=False,realized=0.0)
        if active:
            p=active
            buy=p["sign"]==1
            def hit_stop(price):
                return lo <= price if buy else hi >= price
            def hit_target(price):
                return hi >= price if buy else lo <= price
            def exit_leg(price, fraction):
                adverse = price*(1 - p["sign"]*slippage_fraction)
                return ((adverse-p["entry"])*p["sign"]*p["qty"]*fraction
                        *spec.price_value_per_unit -
                        2*p["qty"]*fraction*spec.commission_per_unit_per_side), adverse
            event=None
            exit_px=None
            # Stops and open gaps take precedence on ambiguous candles.
            stop_price=p["entry"] if p["tp1_hit"] else p["stop"]
            if hit_stop(stop_price):
                raw = min(op,stop_price) if buy else max(op,stop_price)
                fraction = 1-tp1_fraction if p["tp1_hit"] else 1.0
                gain, exit_px=exit_leg(raw,fraction)
                p["realized"]+=gain
                event="BREAKEVEN" if p["tp1_hit"] else "STOP"
            elif p["tp1_hit"] and hit_target(p["tp2"]):
                gain, exit_px=exit_leg(p["tp2"],1-tp1_fraction)
                p["realized"]+=gain
                event="TP2"
            elif not p["tp1_hit"] and hit_target(p["tp1"]):
                gain,_=exit_leg(p["tp1"],tp1_fraction)
                p["realized"]+=gain
                p["tp1_hit"]=True
            elapsed=(current_time-p["started"]).total_seconds()/60
            if event is None and elapsed>=expire_minutes:
                fraction=1-tp1_fraction if p["tp1_hit"] else 1.0
                gain,exit_px=exit_leg(cl,fraction)
                p["realized"]+=gain
                event="EXPIRED"
            if event is not None:
                equity+=p["realized"]
                daily_pnl+=p["realized"]
                records.append(LifecycleTrade(p["side"],p["started"].isoformat(),
                     current_time.isoformat(),p["entry"],p["qty"],p["realized"],
                     event,p["tp1_hit"],exit_px))
                active=None
        if active is None and i in indexed:
            pending=indexed[i]
    if active:
        p=active
        last=bars[-1]
        fraction=1-tp1_fraction if p["tp1_hit"] else 1.0
        adverse=float(last["close"])*(1-p["sign"]*slippage_fraction)
        pnl=((adverse-p["entry"])*p["sign"]*p["qty"]*fraction
             *spec.price_value_per_unit-2*p["qty"]*fraction*
             spec.commission_per_unit_per_side)
        total=p["realized"]+pnl
        equity+=total
        records.append(LifecycleTrade(p["side"],p["started"].isoformat(),
            str(last["time"]),p["entry"],p["qty"],total,"END_OF_TEST",
            p["tp1_hit"],adverse))
    return records,equity
