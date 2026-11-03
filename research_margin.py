"""Broker-parameterized Forex/gold sizing research; NEVER places orders.

All money values must already be converted into account currency.
The leverage is an explicit scenario, NOT a broker default or recommendation.
"""
from dataclasses import dataclass
from math import floor, isfinite
from shared_risk import InstrumentSpec, RiskPolicy

@dataclass(frozen=True)
class MarginScenario:
    leverage: float
    margin_buffer_fraction: float = 0.2
    spread_price: float = 0.0
    slippage_price: float = 0.0

def margin_position_size(equity, entry, stop, spec: InstrumentSpec,
                         scenario: MarginScenario, policy=RiskPolicy(),
                         open_risk=0.0, daily_realized_pnl=0.0):
    """Returns quantity, reason and diagnostic amounts, not an executable order."""
    values=(equity,entry,stop,spec.quantity_step,spec.min_quantity,
            spec.price_value_per_unit,spec.commission_per_unit_per_side,
            scenario.leverage,scenario.margin_buffer_fraction,
            scenario.spread_price,scenario.slippage_price,
            open_risk,daily_realized_pnl)
    if not all(isfinite(x) for x in values):
        return 0.0,"nonfinite input",{}
    if (equity<=0 or entry<=0 or stop<=0 or entry==stop or
        spec.quantity_step<=0 or spec.min_quantity<=0 or
        spec.price_value_per_unit<=0 or spec.commission_per_unit_per_side<0 or
        scenario.leverage<1 or not 0<=scenario.margin_buffer_fraction<1 or
        scenario.spread_price<0 or scenario.slippage_price<0 or
        not 0<policy.risk_fraction<=policy.max_open_risk_fraction<=1 or
        not 0<policy.max_daily_loss_fraction<=1 or
        policy.max_notional_fraction<=0):
        return 0.0,"invalid configuration",{}
    if daily_realized_pnl<=-equity*policy.max_daily_loss_fraction:
        return 0.0,"daily loss limit",{}
    risk_budget=min(equity*policy.risk_fraction,
                    equity*policy.max_open_risk_fraction-open_risk)
    if risk_budget<=0:
        return 0.0,"portfolio risk limit",{}
    unit_risk=((abs(entry-stop)+scenario.spread_price+
                2*scenario.slippage_price)*spec.price_value_per_unit+
               2*spec.commission_per_unit_per_side)
    notional_per_unit=entry*spec.price_value_per_unit
    risk_qty=risk_budget/unit_risk
    # Explicit leverage scenario and additional policy cap both apply.
    margin_qty=(equity*(1-scenario.margin_buffer_fraction)*
                scenario.leverage/notional_per_unit)
    notional_qty=equity*policy.max_notional_fraction*scenario.leverage/notional_per_unit
    qty=floor((min(risk_qty,margin_qty,notional_qty)+1e-12)/
              spec.quantity_step)*spec.quantity_step
    qty=round(qty,12)
    diagnostics={"risk_budget":round(risk_budget,6),
                 "minimum_lot_stop_risk":round(unit_risk*spec.min_quantity,6),
                 "minimum_lot_required_margin":round(
                     notional_per_unit*spec.min_quantity/scenario.leverage,6),
                 "risk_limited_qty":round(risk_qty,12),
                 "margin_limited_qty":round(margin_qty,12),
                 "notional_policy_limited_qty":round(notional_qty,12)}
    if qty+1e-12<spec.min_quantity:
        if risk_qty+1e-12<spec.min_quantity:
            reason="minimum lot exceeds stop-risk budget"
        elif margin_qty+1e-12<spec.min_quantity:
            reason="minimum lot exceeds margin budget"
        else:
            reason="minimum lot exceeds leveraged notional policy cap"
        return 0.0,reason,diagnostics
    return qty,"research-only eligible",diagnostics

def compare_margin_scenarios(bars, signals, capital, spec, leverages=(1,10,30,100),
                             spread_price=0.0, slippage_price=0.0):
    """Screen original signal entries under disclosed hypothetical leverage.

    Fixed starting equity per candidate; ignores concurrent positions, price
    path and margin calls. NOT a profit backtest or broker recommendation.
    """
    scenarios={}
    for leverage in leverages:
        scenario=MarginScenario(leverage=leverage,spread_price=spread_price,
                                slippage_price=slippage_price)
        eligible=0
        rejected={}
        for signal in signals:
            i=signal["bar_index"]
            if not 0<=i<len(bars)-1:
                raise ValueError("invalid signal index")
            qty,reason,_=margin_position_size(
                capital,float(bars[i+1]["open"]),float(signal["stop"]),
                spec,scenario)
            if qty>0:
                eligible+=1
            else:
                rejected[reason]=rejected.get(reason,0)+1
        scenarios[str(leverage)]={
            "candidate_signals":len(signals),
            "sizing_eligible_signals":eligible,
            "rejection_reasons":rejected}
    return {"hypothetical_leverage_scenarios":scenarios,
            "spread_price":spread_price,"slippage_price":slippage_price,
            "warning":"Research-only fixed-equity eligibility screening; "
                      "not simulated trades, profitability, broker eligibility "
                      "or live readiness. Leverage can magnify losses and "
                      "margin calls. Account currency conversion, swaps, "
                      "broker margin rules and actual spread remain unverified."}
