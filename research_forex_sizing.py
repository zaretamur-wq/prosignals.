"""Research-only audit of Forex/gold minimum-lot and margin assumptions.

This intentionally DOES NOT infer broker leverage or override position sizing.
It separates risk-budget failures from cash-notional constraints.
"""
from shared_risk import RiskPolicy, size_position

def forex_sizing_audit(bars, signals, capital, spec, policy=RiskPolicy()):
    if capital <= 0:
        raise ValueError("capital must be positive")
    reasons={}
    examples=[]
    eligible=0
    for signal in signals:
        i=signal["bar_index"]
        if not 0<=i<len(bars)-1:
            raise ValueError("invalid signal index")
        entry=float(bars[i+1]["open"])
        stop=float(signal["stop"])
        qty,reason=size_position(capital,entry,stop,spec,policy)
        if qty>0:
            eligible+=1
            continue
        reasons[reason]=reasons.get(reason,0)+1
        if len(examples)<5:
            minimum_risk=(abs(entry-stop)*spec.price_value_per_unit+
                          2*spec.commission_per_unit_per_side)*spec.min_quantity
            minimum_notional=entry*spec.price_value_per_unit*spec.min_quantity
            examples.append({
                "signal_index":i,"entry":entry,"stop":stop,
                "minimum_order_stop_risk_account_ccy":round(minimum_risk,4),
                "minimum_order_notional_account_ccy":round(minimum_notional,4),
                "risk_budget_account_ccy":round(capital*policy.risk_fraction,4),
                "cash_notional_limit_account_ccy":round(
                    capital*policy.max_notional_fraction,4),
                "reason":reason})
    return {
        "candidate_signals":len(signals),
        "eligible_at_fixed_starting_equity":eligible,
        "rejected_at_fixed_starting_equity":len(signals)-eligible,
        "rejection_reasons":reasons,
        "sample_rejections":examples,
        "warning":"Fixed-equity screening only, not a trading simulation. "
                  "Cash-only notional cap is not broker margin. Do not "
                  "interpret zero positions as a Forex strategy failure. "
                  "Broker-specific leverage, margin, spreads, contract "
                  "sizes and account-currency conversion are required."
    }
