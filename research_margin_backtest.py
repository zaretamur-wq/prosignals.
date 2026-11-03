"""Research-only Forex/gold backtest using explicitly configured margin assumptions.

No live execution. Spread is approximated by adverse half-spread entry and exit
slippage; real bid/ask, swaps, margin calls and FX conversion are not modeled.
"""
from shared_backtest import run_backtest
from shared_risk import RiskPolicy
from research_margin import MarginScenario, margin_position_size

def backtest_margin_scenario(bars, signals, capital, spec, scenario: MarginScenario,
                             policy=RiskPolicy()):
    if scenario.spread_price or scenario.slippage_price:
        # Reject cost parameters until bid/ask fills are modeled accurately.
        raise ValueError("nonzero spread/slippage requires bid-ask fill model")
    def sizing(equity, entry, stop, instrument, risk_policy,
               open_risk=0.0, realized_daily_pnl=0.0):
        qty, reason, _ = margin_position_size(
            equity, entry, stop, instrument, scenario, risk_policy,
            open_risk=open_risk, daily_realized_pnl=realized_daily_pnl)
        return qty, reason
    trades, equity = run_backtest(
        bars, signals, capital, spec, policy, position_sizer=sizing)
    finished = [t for t in trades if t.outcome != "END_OF_TEST"]
    return {
        "hypothetical_leverage": scenario.leverage,
        "signals": len(signals),
        "completed_trades": len(finished),
        "net_pnl": round(equity-capital,6),
        "win_rate": sum(t.pnl>0 for t in finished)/len(finished) if finished else None,
        "warning": "Research-only, zero-spread reference; not executable broker "
                   "results. Spread, swaps, margin calls and account-currency "
                   "conversion remain unmodeled. Leverage magnifies losses."
    }
