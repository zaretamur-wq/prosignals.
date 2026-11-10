"""Research-only consistency screen for precomputed session comparison results.

A session is not robust merely because one holdout half is profitable.
This is diagnostic only; no holdout selection or execution approval.
"""
import math


def wilson_lower_bound(wins, trades, z=1.96):
    """Conservative binomial win-rate bound; diagnostic, not proof of edge."""
    if type(trades) is not int or type(wins) is not int or trades <= 0 or not 0 <= wins <= trades:
        raise ValueError("wins/trades must be valid integers with trades > 0")
    p = wins / trades
    d = 1 + z*z/trades
    return (p + z*z/(2*trades) - z*math.sqrt(p*(1-p)/trades + z*z/(4*trades*trades))) / d


def screen_session(comparison, session, rr=1.0, min_trades_per_half=30):
    if session not in ("london", "ny") or rr not in (1.0, 2.0):
        raise ValueError("Unsupported session or R multiple")
    if type(min_trades_per_half) is not int or min_trades_per_half < 1:
        raise ValueError("min_trades_per_half must be positive")
    reasons = []
    confidence = {}
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
        # The displayed win rate alone cannot justify a 75% claim.
        # A rounded percentage does not identify an exact integer win count;
        # use an explicit count when available, otherwise omit confidence.
        wins = metrics.get("wins")
        if type(wins) is int and 0 <= wins <= metrics["trades"] and metrics["trades"] > 0:
            if abs(100 * wins / metrics["trades"] - metrics["win_rate_pct"]) > 0.11:
                reasons.append(f"{half}_win_count_mismatch")
            else:
                confidence[half] = round(100 * wilson_lower_bound(wins, metrics["trades"]), 2)
        elif wins is not None:
            reasons.append(f"{half}_invalid_wins")
        if metrics["trades"] < min_trades_per_half:
            reasons.append(f"{half}_insufficient_trades")
        if metrics["net_pnl_usd"] <= 0 or metrics["profit_factor"] <= 1:
            reasons.append(f"{half}_unprofitable")
        if not 0 <= metrics["max_drawdown_pct"] <= 15:
            reasons.append(f"{half}_drawdown")
    return {"session": session, "rr": rr, "consistent_across_halves": not reasons,
            "reasons": reasons, "halves": halves, "wilson_95_lower_bound_pct": confidence,
            "note": "Diagnostic on already inspected holdout; NOT independent validation or deployment approval."}
