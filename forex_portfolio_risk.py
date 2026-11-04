"""Research-only shared-account position sizing and exposure guard.

No broker integration or live order capability. Estimates must be supplied
from independently validated symbol-specific pip values and margin models.
"""
from math import floor, isfinite


def size_position(equity_usd, stop_pips, pip_value_usd_per_lot,
                  risk_fraction=0.03, lot_step=0.01, min_lot=0.01,
                  extra_cost_usd_per_lot=0.0, available_margin_usd=None,
                  margin_usd_per_lot=None):
    """Return lot size, or zero if the minimum lot violates risk/margin.

    Costs should include expected entry/exit friction; stops may still gap.
    """
    values = (equity_usd, stop_pips, pip_value_usd_per_lot,
              risk_fraction, lot_step, min_lot, extra_cost_usd_per_lot)
    if not all(isfinite(v) for v in values):
        raise ValueError("Nonfinite sizing input")
    if not (equity_usd > 0 and stop_pips > 0 and pip_value_usd_per_lot > 0
            and 0 < risk_fraction <= 0.03 and lot_step > 0 and min_lot > 0
            and extra_cost_usd_per_lot >= 0):
        raise ValueError("Invalid sizing input")
    if available_margin_usd is not None or margin_usd_per_lot is not None:
        if available_margin_usd is None or margin_usd_per_lot is None:
            raise ValueError("Both margin inputs are required")
        if not all(isfinite(v) for v in (available_margin_usd, margin_usd_per_lot)):
            raise ValueError("Nonfinite margin input")
        if available_margin_usd < 0 or margin_usd_per_lot <= 0:
            raise ValueError("Invalid margin input")
    per_lot_risk = stop_pips * pip_value_usd_per_lot + extra_cost_usd_per_lot
    allowed = equity_usd * risk_fraction
    units = floor((allowed / per_lot_risk) / lot_step + 1e-10)
    lots = round(units * lot_step, 8)
    if lots + 1e-10 < min_lot:
        return 0.0
    if available_margin_usd is not None:
        margin_units = floor((available_margin_usd / margin_usd_per_lot) / lot_step + 1e-10)
        lots = min(lots, round(margin_units * lot_step, 8))
    return lots if lots + 1e-10 >= min_lot else 0.0


def can_add_position(open_risk_usd, new_risk_usd, equity_usd,
                     max_combined_risk_fraction=0.03):
    """Check aggregate *planned* stop exposure before opening another trade."""
    values = (open_risk_usd, new_risk_usd, equity_usd, max_combined_risk_fraction)
    if not all(isfinite(v) for v in values):
        raise ValueError("Nonfinite exposure input")
    if (open_risk_usd < 0 or new_risk_usd <= 0 or equity_usd <= 0
            or not 0 < max_combined_risk_fraction <= 0.03):
        raise ValueError("Invalid exposure input")
    return open_risk_usd + new_risk_usd <= equity_usd * max_combined_risk_fraction + 1e-9
