"""Shared position sizing for Forex, gold and crypto PAPER testing.

Contract value, FX conversion, leverage, spread and margin requirements vary
by broker. Configure instrument parameters before use; never send live orders.
"""
from dataclasses import dataclass
from math import floor, isfinite

@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    quantity_step: float
    min_quantity: float
    price_value_per_unit: float = 1.0
    commission_per_unit_per_side: float = 0.0

@dataclass(frozen=True)
class RiskPolicy:
    risk_fraction: float = 0.005
    max_open_risk_fraction: float = 0.02
    max_daily_loss_fraction: float = 0.02
    max_notional_fraction: float = 1.0

def size_position(equity, entry, stop, spec: InstrumentSpec, policy: RiskPolicy,
                  open_risk=0.0, realized_daily_pnl=0.0, available_cash=None):
    """Return (quantity, explanation), using values converted to account currency."""
    vals = (equity, entry, stop, spec.quantity_step, spec.min_quantity,
            spec.price_value_per_unit, open_risk, realized_daily_pnl,
            spec.commission_per_unit_per_side)
    if not all(isfinite(v) for v in vals) or equity <= 0 or entry <= 0 or stop <= 0:
        return 0.0, "invalid prices or account balance"
    if (spec.quantity_step <= 0 or spec.min_quantity <= 0
            or spec.price_value_per_unit <= 0 or spec.commission_per_unit_per_side < 0):
        return 0.0, "invalid instrument specification"
    if not 0 < policy.risk_fraction <= policy.max_open_risk_fraction <= 1:
        return 0.0, "invalid risk policy"
    if not 0 < policy.max_daily_loss_fraction <= 1 or policy.max_notional_fraction <= 0:
        return 0.0, "invalid risk policy"
    if entry == stop:
        return 0.0, "zero stop distance"
    if realized_daily_pnl <= -equity * policy.max_daily_loss_fraction:
        return 0.0, "daily loss limit reached"
    budget = min(equity * policy.risk_fraction,
                 equity * policy.max_open_risk_fraction - open_risk)
    if budget <= 0:
        return 0.0, "portfolio risk limit reached"
    per_unit_risk = (abs(entry-stop) * spec.price_value_per_unit
                     + 2 * spec.commission_per_unit_per_side)
    if per_unit_risk <= 0:
        return 0.0, "invalid unit risk"
    qty_risk = budget / per_unit_risk
    qty_notional = (equity * policy.max_notional_fraction
                    / (entry * spec.price_value_per_unit))
    if available_cash is not None:
        if not isfinite(available_cash) or available_cash < 0:
            return 0.0, "invalid available cash"
        qty_notional = min(qty_notional, available_cash /
                           (entry * spec.price_value_per_unit))
    qty = floor((min(qty_risk, qty_notional) + 1e-12)
                / spec.quantity_step) * spec.quantity_step
    qty = round(qty, 12)
    if qty + 1e-12 < spec.min_quantity:
        return 0.0, "minimum order size exceeds risk/notional allowance"
    return qty, "ok"
