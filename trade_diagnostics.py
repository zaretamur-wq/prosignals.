"""Transparent paper-only ProSignals trade diagnostics.

Joins fills to candidate signals by actual next-bar entry time AND side.
Reports only observed simulation outcomes, not causal explanations.
No exchange orders, predictive classification, or optimization.
"""
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _utc(value):
    value = str(value).replace("Z", "+00:00")
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return ts.astimezone(timezone.utc).isoformat()


def _bucket(score):
    if score is None:
        return "unknown"
    score = float(score)
    if score < 75:
        return "below75"
    if score < 80:
        return "75-79"
    if score < 85:
        return "80-84"
    if score < 90:
        return "85-89"
    return "90+"


def build_report(bars, signals, trades, starting_capital):
    """Return a trade ledger plus descriptive statistics on completed trades.

    The entry-time match is an audit hint, NOT proof the historical signal had
    access to point-in-time non-OHLC data. Null score means unmatched.
    """
    if starting_capital <= 0:
        raise ValueError("starting_capital must be positive")
    candidates = defaultdict(list)
    for s in signals:
        i = s["bar_index"]
        if not isinstance(i, int) or i < 0 or i + 1 >= len(bars):
            raise ValueError("signal missing a next candle")
        key = (_utc(bars[i + 1]["time"]), s["side"])
        candidates[key].append(s)
    rows = []
    for n, trade in enumerate(trades, 1):
        key = (_utc(trade.entry_time), trade.side)
        matches = candidates.get(key, [])
        # Ambiguous match must be marked rather than guessed.
        signal = matches[0] if len(matches) == 1 else None
        score = signal.get("score") if signal else None
        row = {
            "trade_id": n,
            "entry_time": key[0],
            "exit_time": _utc(trade.exit_time),
            "side": trade.side,
            "entry_price": trade.entry,
            "exit_price": trade.exit_price if hasattr(trade,"exit_price") else trade.exit,
            "quantity": trade.quantity,
            "net_pnl": trade.pnl,
            "outcome": trade.outcome,
            "tp1_hit": bool(getattr(trade,"tp1_hit",False)),
            "signal_score": score,
            "score_bucket": _bucket(score),
            "signal_match": "matched" if signal else ("ambiguous" if matches else "unmatched"),
        }
        rows.append(row)
    completed = [r for r in rows if r["outcome"] != "END_OF_TEST"]
    def stats(group):
        wins = [r["net_pnl"] for r in group if r["net_pnl"] > 0]
        losses = [r["net_pnl"] for r in group if r["net_pnl"] < 0]
        gross_profit = sum(wins)
        gross_loss = -sum(losses)
        return {
            "count": len(group),
            "positive_net_trades": len(wins),
            "win_rate": len(wins) / len(group) if group else None,
            "net_pnl": sum(r["net_pnl"] for r in group),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": gross_profit / gross_loss if gross_loss else None,
            "mean_net_pnl": sum(r["net_pnl"] for r in group)/len(group) if group else None,
        }
    by_score = {}
    for name in ["below75","75-79","80-84","85-89","90+","unknown"]:
        sample = [r for r in completed if r["score_bucket"] == name]
        if sample:
            by_score[name] = stats(sample)
    by_side = {side:stats([r for r in completed if r["side"] == side])
               for side in ("BUY","SELL")}
    by_outcome = {outcome:stats([r for r in completed if r["outcome"] == outcome])
                  for outcome in sorted({r["outcome"] for r in completed})}
    peak = equity = float(starting_capital)
    max_dd = 0.0
    # Completed trades can exit out of entry order; chronology matters.
    for row in sorted(rows,key=lambda r:(r["exit_time"],r["trade_id"])):
        equity += row["net_pnl"]
        peak = max(peak,equity)
        max_dd = max(max_dd, (peak-equity)/peak)
    return {
        "summary": {
            "total_signals":len(signals),
            "executed_positions":len(rows),
            "completed_positions":len(completed),
            "unmatched_positions":sum(r["signal_match"] != "matched" for r in rows),
            "completed":stats(completed),
            "max_realized_drawdown_pct":round(max_dd*100,3),
            "end_of_test_positions":len(rows)-len(completed),
        },
        "by_score_bucket":by_score,
        "by_side":by_side,
        "by_outcome":by_outcome,
        "ledger":rows,
        "limitations":(
            "Simulated outcomes only; no causality inferred. Completed positions "
            "exclude END_OF_TEST. Missing venue data, spread, margin, calendar, "
            "multi-position execution or liquidity can invalidate real-world "
            "inferences. Signal scores are not probabilities."
        )
    }


def save_report(report, destination, symbol):
    """Write per-trade CSV and aggregate JSON to caller-controlled directory."""
    directory=Path(destination)
    directory.mkdir(parents=True,exist_ok=True)
    stem="".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "-_")
    if not stem:
        raise ValueError("invalid report symbol")
    ledger_path=directory / (stem+"_trades.csv")
    report_path=directory / (stem+"_diagnostics.json")
    columns=["trade_id","entry_time","exit_time","side","entry_price",
             "exit_price","quantity","net_pnl","outcome","tp1_hit",
             "signal_score","score_bucket","signal_match"]
    with ledger_path.open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=columns)
        writer.writeheader()
        writer.writerows(report["ledger"])
    with report_path.open("w",encoding="utf-8") as file:
        json.dump({k:v for k,v in report.items() if k!="ledger"},file,indent=2,
                  allow_nan=False)
    return str(ledger_path),str(report_path)
