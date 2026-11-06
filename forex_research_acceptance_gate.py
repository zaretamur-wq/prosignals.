"""Fail-closed acceptance gate for exploratory Forex strategy comparisons.

Never treats holdout-picked variants as an untouched out-of-sample validation.
No live execution or broker access.
"""
import argparse
import json
from pathlib import Path


def assess(comparison, candidate, min_trades=100, min_profit_factor=1.2,
           max_drawdown_pct=15.0, min_win_rate_pct=75.0):
    if min_trades < 1 or min_profit_factor <= 1 or not 0 < max_drawdown_pct <= 100 or not 0 < min_win_rate_pct <= 100:
        raise ValueError("Invalid acceptance thresholds")
    result = comparison.get("results", {}).get(candidate)
    reasons = []
    if not isinstance(result, dict):
        return {"candidate": candidate, "accepted": False, "reasons": ["candidate_missing"]}
    for partition in ("train", "holdout"):
        metrics = result.get(partition)
        if not isinstance(metrics, dict):
            reasons.append(partition + "_missing")
            continue
        for key in ("trades", "win_rate_pct", "profit_factor", "max_drawdown_pct", "net_pnl_usd"):
            value = metrics.get(key)
            if not isinstance(value, (int, float)) or not __import__("math").isfinite(value):
                reasons.append(partition + "_" + key + "_missing_or_invalid")
        if any(x.startswith(partition + "_") for x in reasons):
            continue
        if metrics["trades"] < min_trades:
            reasons.append(partition + "_insufficient_trades")
        if metrics["win_rate_pct"] < min_win_rate_pct:
            reasons.append(partition + "_win_rate_below_target")
        if metrics["profit_factor"] < min_profit_factor:
            reasons.append(partition + "_profit_factor_below_minimum")
        if metrics["max_drawdown_pct"] > max_drawdown_pct:
            reasons.append(partition + "_drawdown_above_limit")
        if metrics["net_pnl_usd"] <= 0:
            reasons.append(partition + "_nonpositive_profit")
    # Even good exploratory metrics cannot approve broker execution.
    reasons.append("independent_forward_and_broker_validation_required")
    return {"candidate": candidate, "accepted": False, "research_metrics_pass": len(reasons) == 1,
            "reasons": reasons, "note": "Holdout was inspected during candidate selection; fresh unseen data required."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("comparison_json")
    p.add_argument("--candidate", required=True)
    p.add_argument("--output")
    a = p.parse_args()
    result = assess(json.loads(Path(a.comparison_json).read_text()), a.candidate)
    payload = json.dumps(result, indent=2) + "\n"
    if a.output:
        Path(a.output).write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
