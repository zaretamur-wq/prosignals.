"""Conservative, signal-only Forex CSV backtester for XM Standard research.

CSV columns: time,open,high,low,close (UTC timestamps).
Optional columns: spread_pips. Never sends orders.
Usage: python forex_backtest.py candles.csv --spread-pips 1.5
"""
import argparse
import json
import pandas as pd
import numpy as np
from forex_daily_risk import DailyRiskGuard

PIP = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "XAUUSD": 0.01}
PIP_VALUE_PER_LOT = {"EURUSD": 10.0, "GBPUSD": 10.0}  # USD account, approximate
def backtest(df, symbol="EURUSD", initial=100.0, risk_pct=0.03,
             spread_pips=1.5, slippage_pips=0.2, min_lot=0.01,
             daily_profit_target=15.0, daily_loss_limit=6.0):
    if not (initial > 0 and 0 < risk_pct <= 0.03 and min_lot > 0 and slippage_pips >= 0 and spread_pips >= 0):
        raise ValueError("Invalid initial balance, risk (0-3%), lot step, spread or slippage")
    if symbol not in PIP_VALUE_PER_LOT:
        raise ValueError("Only EURUSD and GBPUSD supported until symbol-specific pip value is verified")
    required = {"time", "open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required-set(df.columns)}")
    d = df.copy()
    d["time"] = pd.to_datetime(d["time"], utc=True)
    d = d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    if len(d) < 220:
        raise ValueError("Need >=220 chronological candles")
    for c in ["open", "high", "low", "close"]:
        d[c] = pd.to_numeric(d[c], errors="raise")
    if d[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("Missing OHLC values")
    if ((d["high"] < d[["open", "close", "low"]].max(axis=1)) |
        (d["low"] > d[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC")
    pip = PIP[symbol]
    close = d["close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    tr = pd.concat([(d.high-d.low), (d.high-close.shift()).abs(),
                    (d.low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False).mean()
    cash, peak, max_dd, trades = initial, initial, 0.0, []
    daily_guard = DailyRiskGuard(daily_profit_target, daily_loss_limit)
    i = 201
    while i < len(d)-1:
        if not daily_guard.can_open(d.time.iloc[i+1]):
            i += 1
            continue
        # Signal uses only COMPLETED candle i; entry occurs next candle.
        buy = ema20.iloc[i] > ema50.iloc[i] and close.iloc[i-1] <= ema20.iloc[i-1] and close.iloc[i] > ema20.iloc[i]
        sell = ema20.iloc[i] < ema50.iloc[i] and close.iloc[i-1] >= ema20.iloc[i-1] and close.iloc[i] < ema20.iloc[i]
        if not (buy or sell) or not np.isfinite(atr.iloc[i]) or atr.iloc[i] <= 0:
            i += 1
            continue
        direction = 1 if buy else -1
        sp = float(d.iloc[i+1].get("spread_pips", spread_pips))
        if not np.isfinite(sp) or sp < 0:
            raise ValueError("Invalid spread")
        # Mid OHLC input: buy opens at ask, sell opens at bid.
        entry = float(d.open.iloc[i+1]) + direction*(sp/2+slippage_pips)*pip
        distance = max(float(atr.iloc[i])*1.5, 5*pip)
        sl = entry-direction*distance
        tp = entry+direction*2*distance
        risk_per_lot = distance/pip*PIP_VALUE_PER_LOT[symbol]
        # Include exit slippage and a gap allowance in planned risk budget.
        budget_per_lot = risk_per_lot + slippage_pips*PIP_VALUE_PER_LOT[symbol]
        lots = round(np.floor((cash*risk_pct/budget_per_lot)/min_lot + 1e-10)*min_lot, 8)
        if lots < min_lot:
            i += 1
            continue
        exit_price, outcome, j = None, None, i+1
        while j < len(d):
            bar = d.iloc[j]
            sp_j = float(bar.get("spread_pips", spread_pips))
            if not np.isfinite(sp_j) or sp_j < 0:
                raise ValueError("Invalid spread")
            # Long exits at bid; short exits at ask.
            exit_low = float(bar.low) - direction*sp_j*pip/2
            exit_high = float(bar.high) - direction*sp_j*pip/2
            stop_hit = exit_low <= sl if buy else exit_high >= sl
            tp_hit = exit_high >= tp if buy else exit_low <= tp
            if stop_hit or tp_hit:
                # Both in same candle -> conservative stop-first assumption.
                outcome = "SL" if stop_hit else "TP"
                exit_price = sl if stop_hit else tp
                # Gap through stop: worse open price; no favorable TP improvement.
                open_exit = float(bar.open)-direction*sp_j*pip/2
                if stop_hit and direction*(open_exit-sl) < 0:
                    exit_price = open_exit
                exit_price -= direction*slippage_pips*pip
                break
            j += 1
        if exit_price is None:
            break  # Do not score an unclosed trade as a win.
        pnl = direction*(exit_price-entry)/pip*PIP_VALUE_PER_LOT[symbol]*lots
        cash += pnl
        daily_guard.record_exit(d.time.iloc[j], pnl)
        peak = max(peak, cash)
        max_dd = max(max_dd, (peak-cash)/peak)
        trades.append({"entry_time":str(d.time.iloc[i+1]),"exit_time":str(d.time.iloc[j]),
                       "side":"BUY" if buy else "SELL","lots":float(lots),
                       "pnl_usd":round(pnl,2),"outcome":outcome})
        if cash <= 0:
            break
        i = j+1  # one trade at a time
    wins = sum(t["pnl_usd"]>0 for t in trades)
    return {"symbol":symbol,"initial_usd":initial,"final_usd":round(cash,2),
            "trades":len(trades),"win_rate_pct":round(100*wins/len(trades),2) if trades else None,
            "max_drawdown_pct":round(100*max_dd,2),"risk_pct_per_trade":risk_pct*100,
            "assumptions":"mid-price OHLC; spread both sides; slippage entry/exit; stop-first ambiguity; no commissions, swaps, or margin modeling",
            "skipped_small_account_warning": "At $100, 0.01-lot minimum may still prevent trades at 3% risk.",
            "daily_realized_pnl_usd":daily_guard.summary(),
            "daily_profit_target_usd":daily_profit_target,
            "daily_loss_limit_usd":daily_loss_limit,
            "daily_limit_note":"Entry gating on UTC realized P&L; overnight positions and gaps can exceed limits.",
            "trade_log":trades}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--symbol",choices=list(PIP_VALUE_PER_LOT),default="EURUSD")
    p.add_argument("--spread-pips",type=float,default=1.5)
    p.add_argument("--risk-pct",type=float,default=0.03)
    p.add_argument("--daily-profit-target",type=float,default=15.0)
    p.add_argument("--daily-loss-limit",type=float,default=6.0)
    args=p.parse_args()
    result=backtest(pd.read_csv(args.csv),symbol=args.symbol,
                    spread_pips=args.spread_pips,risk_pct=args.risk_pct,
                    daily_profit_target=args.daily_profit_target,
                    daily_loss_limit=args.daily_loss_limit)
    print(json.dumps(result,indent=2))
