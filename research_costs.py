"""Research-only cost sensitivity using identical signals and candles.

No parameter fitting: this shows whether the strategy survives realistic
transaction-cost assumptions. Rates are per side of trade notional.
"""
from trade_lifecycle import backtest_lifecycle
from shared_risk import RiskPolicy


def cost_sensitivity(bars, signals, capital, instrument, expire_minutes,
                     baseline_fee_rate, baseline_slippage):
    if baseline_fee_rate < 0 or baseline_slippage < 0:
        raise ValueError("negative costs")
    scenarios = (
        ("zero_cost_reference", 0.0, 0.0),
        ("baseline", baseline_fee_rate, baseline_slippage),
        ("double_cost_stress", 2 * baseline_fee_rate,
         2 * baseline_slippage),
    )
    output={}
    for name,fee,slippage in scenarios:
        trades,equity=backtest_lifecycle(
            bars,signals,capital,instrument,RiskPolicy(),
            expire_minutes=expire_minutes,fee_rate=fee,
            slippage_fraction=slippage)
        completed=[t for t in trades if t.outcome!="END_OF_TEST"]
        profit=sum(t.pnl for t in completed if t.pnl>0)
        loss=-sum(t.pnl for t in completed if t.pnl<0)
        output[name]={
            "fee_rate_per_side":fee,
            "slippage_fraction":slippage,
            "executed_positions":len(trades),
            "completed_positions":len(completed),
            "win_rate":(sum(t.pnl>0 for t in completed)/len(completed)
                        if completed else None),
            "net_pnl":equity-capital,
            "profit_factor":profit/loss if loss else None,
        }
    output["warning"]=(
        "Cost scenarios use identical historical candidate signals, but "
        "position sizing may vary with equity. Spread, funding, market impact "
        "and live fills remain unmodeled. Zero-cost results are NOT tradable.")
    return output
