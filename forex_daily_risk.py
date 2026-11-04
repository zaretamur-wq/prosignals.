"""Research-only daily realized P&L guard. No order execution.

This guard blocks *new* entries after a daily threshold is reached.
Open positions, gaps, and slippage can still exceed limits.
Dates are UTC, based on the provided timestamp.
"""
from datetime import datetime, timezone
from math import isfinite


class DailyRiskGuard:
    def __init__(self, profit_target_usd=15.0, loss_limit_usd=6.0):
        if not (isfinite(profit_target_usd) and isfinite(loss_limit_usd)
                and profit_target_usd > 0 and loss_limit_usd > 0):
            raise ValueError("Daily thresholds must be positive")
        self.profit_target_usd = float(profit_target_usd)
        self.loss_limit_usd = float(loss_limit_usd)
        self.realized = {}

    @staticmethod
    def day(timestamp):
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return timestamp.astimezone(timezone.utc).date().isoformat()

    def record_exit(self, timestamp, pnl_usd):
        if not isfinite(pnl_usd):
            raise ValueError("Realized P&L must be finite")
        key = self.day(timestamp)
        self.realized[key] = self.realized.get(key, 0.0) + float(pnl_usd)
        return self.realized[key]

    def can_open(self, timestamp):
        pnl = self.realized.get(self.day(timestamp), 0.0)
        return -self.loss_limit_usd < pnl < self.profit_target_usd

    def summary(self):
        return dict(sorted(self.realized.items()))
