"""Pure research-only daily entry policy; no broker, orders or Telegram hooks.

Trade P&L must be NET of spread, slippage, fees, swap and commissions.
The policy cannot guarantee a profitable day or a minimum trade count.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

@dataclass(frozen=True)
class DayDecision:
    allow: bool
    reason: str
    risk_pct: float

def _utc_day(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("UTC-aware timestamps required")
    return value.astimezone(timezone.utc).date()

def decide_daily_entry(trades, now, *, max_entries=5, stop_after_wins=3,
                       max_consecutive_losses=2, loss_halt_usd=6.0,
                       initial_risk_pct=1.0, reduced_risk_pct=0.5):
    """trades: completed trades with 'closed_at' and 'net_pnl_usd' fields.
    An unfilled signal is not a trade. Open positions are managed elsewhere.
    """
    if not (3 <= max_entries <= 5 and stop_after_wins == 3
            and max_consecutive_losses in (1, 2)
            and isfinite(loss_halt_usd) and loss_halt_usd > 0
            and 0 < reduced_risk_pct <= initial_risk_pct <= 3):
        raise ValueError("Invalid research risk configuration")
    day = _utc_day(now)
    daily = []
    for t in trades:
        p = float(t["net_pnl_usd"])
        if not isfinite(p):
            raise ValueError("Nonfinite trade P&L")
        if _utc_day(t["closed_at"]) == day:
            daily.append(p)
    total = sum(daily)
    wins = sum(p > 0 for p in daily)
    streak = 0
    for p in reversed(daily):
        if p < 0:
            streak += 1
        else:
            break
    risk = reduced_risk_pct if streak else initial_risk_pct
    if total <= -loss_halt_usd:
        return DayDecision(False, "realized_daily_loss_halt", 0.0)
    if wins >= stop_after_wins:
        return DayDecision(False, "three_wins_completed", 0.0)
    if len(daily) >= max_entries:
        return DayDecision(False, "daily_trade_cap", 0.0)
    if streak >= max_consecutive_losses:
        return DayDecision(False, "consecutive_loss_halt", 0.0)
    return DayDecision(True, "eligible_if_signal_and_broker_checks_pass", risk)
