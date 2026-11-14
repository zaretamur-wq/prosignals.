"""Research-only minimum-lot stop-distance feasibility, NOT broker order sizing.

Computes a necessary (not sufficient) stop-distance bound in quote-price units.
Assumes price_value_per_unit is already converted to account currency, and
commission_per_unit_per_side is in account currency. Spread/slippage must be
provided explicitly as adverse price distances. No broker margin is inferred.
"""
from math import isfinite
from shared_risk import InstrumentSpec


def minimum_lot_stop_feasibility(
    equity: float,
    spec: InstrumentSpec,
    risk_fraction: float = 0.03,
    adverse_spread_price: float = 0.0,
    adverse_slippage_price: float = 0.0,
):
    values = (equity, risk_fraction, spec.min_quantity, spec.quantity_step,
              spec.price_value_per_unit, spec.commission_per_unit_per_side,
              adverse_spread_price, adverse_slippage_price)
    if not all(isfinite(x) for x in values):
        raise ValueError("all inputs must be finite")
    if (equity <= 0 or not 0 < risk_fraction <= 1 or
        spec.min_quantity <= 0 or spec.quantity_step <= 0 or
        spec.price_value_per_unit <= 0 or spec.commission_per_unit_per_side < 0 or
        adverse_spread_price < 0 or adverse_slippage_price < 0):
        raise ValueError("invalid capital, contract, risk, or trading cost")
    # This is the most generous possible stop bound, before margin checks.
    budget = equity * risk_fraction
    round_trip_commission = 2 * spec.commission_per_unit_per_side * spec.min_quantity
    adverse_execution_cost = ((adverse_spread_price + adverse_slippage_price) *
                              spec.price_value_per_unit * spec.min_quantity)
    remaining = budget - round_trip_commission - adverse_execution_cost
    maximum_stop_price_distance = max(0.0, remaining /
                                      (spec.price_value_per_unit * spec.min_quantity))
    return {
        "symbol": spec.symbol,
        "equity": equity,
        "minimum_quantity": spec.min_quantity,
        "risk_budget_account_ccy": round(budget, 6),
        "cost_reserve_account_ccy": round(
            round_trip_commission + adverse_execution_cost, 6),
        "maximum_stop_price_distance": round(maximum_stop_price_distance, 6),
        "feasible_positive_stop": remaining > 0,
        "margin_verified": False,
        "broker_execution_verified": False,
        "note": "Necessary stop-distance ceiling only; not proof of margin, "
                "broker stop-level eligibility, fills, or profitable signals. "
                "Swap, gaps and extra slippage may exceed budget.",
    }
