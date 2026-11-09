"""Research-only consistency screen for precomputed session comparison results.

A session is not robust merely because one holdout half is profitable.
This is diagnostic only; no holdout selection or execution approval.
"""
import math


def screen_session(comparison, session, rr=1.0, min_trades_per_half=30):
    if session not in ("london", "ny") or rr not in (1.0, 2.0):
        raise ValueError("Unsupported session or R multiple")
    if type(min_trades_per_half) is not int or min_trades_per_half < 1:
        raise ValueError("min_trades_per_half must be positive")
    reasons = []
    halves = {}
    for half in ("first", "second"):
        key = f"{'london' if session == 'london' else 'ny'}_holdout_{half}_{rr}R"
        metrics = comparison.get("results", {}).get(key, {}).get("holdout")
        if not isinstance(metrics, dict):
            reasons.append(f"{half}_missing")
            continue
        halves[half] = metrics
        required = ("trades", "win_rate_pct", "net_pnl_usd", "profit_factor", "max_drawdown_pct")
        if any(type(metrics.get(k)) not in (int, float) or not math.isfinite(metrics[k]) for k in required):
            reasons.append(f"{half}_invalid")
            continue
        if (type(metrics["trades"]) is not int or metrics["trades"] < 0
                or not 0 <= metrics["win_rate_pct"] <= 100
                or metrics["profit_factor"] < 0
                or not 0 <= metrics["max_drawdown_pct"] <= 100):
            reasons.append(f"{half}_invalid_range")
            continue
        if metrics["trades"] < min_trades_per_half:
            reasons.append(f"{half}_insufficient_trades")
        if metrics["net_pnl_usd"] <= 0 or metrics["profit_factor"] <= 1:
            reasons.append(f"{half}_unprofitable")
        if not 0 <= metrics["max_drawdown_pct"] <= 15:
            reasons.append(f"{half}_drawdown")
    return {"session": session, "rr": rr, "consistent_across_halves": not reasons,
            "reasons": reasons, "halves": halves,
            "note": "Diagnostic on already inspected holdout; NOT independent validation or deployment approval."}
