"""Offline XM Standard Forex H1 research; no orders or credentials.
Assumed spreads and leverage are SCENARIOS, not verified XM account terms.
Runs independent closed-bar entries with next-open execution and conservative
stop-first OHLC exits. One position at a time; no overlapping signals.
"""
import argparse
import json
from pathlib import Path
from historical_replay import load_csv
from research_entry_candidates import generate

CONTRACT = 100000
MIN_LOT = 0.01
LOT_STEP = 0.01
SPREAD_PIPS = {"EURUSD": 1.8, "GBPUSD": 2.2, "USDJPY": 2.0}
PIP = {"EURUSD": .0001, "GBPUSD": .0001, "USDJPY": .01}

def usd_value(symbol, price, quote_amount):
    return quote_amount / price if symbol == "USDJPY" else quote_amount

def run(df, symbol, signals, start, end, risk_fraction, rr, spread_pips, leverage):
    cash = 100.0
    peak = cash
    max_dd = 0.0
    trades = []
    last_exit = start
    half_spread = spread_pips * PIP[symbol] / 2
    for sig in signals:
        i = sig["bar_index"]
        if i < max(start, last_exit) or i + 1 >= end:
            continue
        direction = 1 if sig["side"] == "BUY" else -1
        mid_entry = float(df.iloc[i+1]["open"])
        entry = mid_entry + direction * half_spread
        stop = float(sig["stop"])
        distance = direction * (entry - stop)
        if distance <= 0:
            continue
        risk_one_lot = usd_value(symbol, entry, distance * CONTRACT)
        lots = int((cash * risk_fraction / risk_one_lot + 1e-10) / LOT_STEP) * LOT_STEP
        lots = round(lots, 2)
        if lots < MIN_LOT:
            continue
        # Margin is an approximate screening assumption; broker details may differ.
        margin = CONTRACT * lots * (1 if symbol == "USDJPY" else entry) / leverage
        if margin > cash:
            continue
        target = entry + direction * distance * rr
        # Intrabar prices are midpoint candles; translate to bid for buys,
        # ask for sells. Stop is favored on ambiguous same-bar touches.
        exit_price = None
        exit_idx = end-1
        for j in range(i+1, end):
            bar = df.iloc[j]
            bid_low = float(bar["low"]) - half_spread
            bid_high = float(bar["high"]) - half_spread
            ask_low = float(bar["low"]) + half_spread
            ask_high = float(bar["high"]) + half_spread
            stop_hit = bid_low <= stop if direction == 1 else ask_high >= stop
            take_hit = bid_high >= target if direction == 1 else ask_low <= target
            if stop_hit or take_hit:
                exit_price = stop if stop_hit else target
                exit_idx = j
                break
        if exit_price is None:
            exit_price = float(df.iloc[end-1]["close"]) - direction * half_spread
        pnl = usd_value(symbol, exit_price, direction * (exit_price-entry)*CONTRACT*lots)
        cash += pnl
        peak = max(peak, cash)
        max_dd = max(max_dd, (peak-cash)/peak)
        trades.append(round(pnl, 5))
        last_exit = exit_idx + 1
        if cash <= 0:
            break
    wins = sum(x>0 for x in trades)
    gross_profit = sum(max(x,0) for x in trades)
    gross_loss = -sum(min(x,0) for x in trades)
    return {"trades":len(trades),"wins":wins,
            "win_rate_pct":round(100*wins/len(trades),2) if trades else None,
            "net_pnl_usd":round(cash-100,2),
            "ending_equity_usd":round(cash,2),
            "max_drawdown_pct":round(max_dd*100,2),
            "profit_factor":round(gross_profit/gross_loss,3) if gross_loss else None}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--symbol",choices=list(PIP),required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--spread-pips",type=float)
    p.add_argument("--leverage",type=float,default=100)
    a=p.parse_args()
    if a.leverage <= 0 or (a.spread_pips is not None and a.spread_pips < 0):
        p.error("leverage must be positive and spread nonnegative")
    df=load_csv(a.csv)
    if len(df)<300:
        p.error("at least 300 candles required")
    spread=SPREAD_PIPS[a.symbol] if a.spread_pips is None else a.spread_pips
    split=int(len(df)*.7)
    report={"symbol":a.symbol,"account":"XM Standard (assumed 100000 base units per lot)",
            "sample_candles":len(df),"train_candles":split,"holdout_candles":len(df)-split,
            "assumed_spread_pips":spread,"assumed_leverage":a.leverage,
            "starting_equity_usd":100,"minimum_lot":MIN_LOT,"results":{},
            "caveats":["Research only; no live trading.",
                       "Spreads, leverage, minimum lots, commissions and swaps require broker verification.",
                       "No commission, slippage, swap or news filter modeled; results optimistic in those respects.",
                       "H1 midpoint OHLC cannot resolve intrabar path; stop first when both hit.",
                       "Train and holdout results share no positions; models have not been optimized."]}
    for method in ("pullback","breakout","range"):
        signals=generate(df,method)
        report["results"][method]={}
        for risk in (.005,.01,.02):
            for rr in (1.0,1.5,2.0):
                key=f"risk_{risk*100:g}pct_rr_{rr:g}"
                report["results"][method][key]={
                    "train":run(df,a.symbol,signals,0,split,risk,rr,spread,a.leverage),
                    "holdout":run(df,a.symbol,signals,split,len(df),risk,rr,spread,a.leverage)}
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
