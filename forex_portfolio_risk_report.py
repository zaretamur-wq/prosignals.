"""Offline research-only validation for multi-pair risk budgets.

This module does not execute trades or make entry decisions.
"""
from math import isfinite


def evaluate_portfolio_risk(equity_usd, planned_risks_usd, margin_requirements_usd=None,
                            available_margin_usd=None, max_risk_fraction=0.03):
    """Summarize hypothetical aggregate stop-loss exposure and margin use."""
    if not isfinite(equity_usd) or equity_usd <= 0:
        raise ValueError("Equity must be finite and positive")
    if not isfinite(max_risk_fraction) or not 0 < max_risk_fraction <= 0.03:
        raise ValueError("Invalid risk fraction")
    risks = list(planned_risks_usd)
    if not all(isfinite(x) and x >= 0 for x in risks):
        raise ValueError("Invalid hypothetical risks")
    total_risk = sum(risks)
    risk_budget = equity_usd * max_risk_fraction
    result = {
        "mode": "offline_hypothetical_risk_report",
        "positions": len(risks),
        "total_planned_risk_usd": round(total_risk, 8),
        "risk_budget_usd": round(risk_budget, 8),
        "within_risk_budget": total_risk <= risk_budget + 1e-9,
    }
    if margin_requirements_usd is not None:
        margins = list(margin_requirements_usd)
        if len(margins) != len(risks) or not all(isfinite(x) and x >= 0 for x in margins):
            raise ValueError("Invalid hypothetical margin requirements")
        if available_margin_usd is None or not isfinite(available_margin_usd) or available_margin_usd < 0:
            raise ValueError("Valid available margin required")
        total_margin = sum(margins)
        result["total_margin_usd"] = round(total_margin, 8)
        result["within_margin_budget"] = total_margin <= available_margin_usd + 1e-9
    return result
