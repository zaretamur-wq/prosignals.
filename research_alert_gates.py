"""Research-only replay of the crypto alert timing gates.

Applies the bot's cooldown and daily alert cap to candidate timestamps.
Does NOT reconstruct the bot's actual open-signal tracking, news calendar,
BTC cross-asset state, or whether a Telegram alert was delivered.
"""
from datetime import datetime, timezone, timedelta


def alert_timing_gate(bars, signals, cooldown_minutes=30, max_daily_alerts=12,
                      candle_minutes=5):
    if cooldown_minutes < 0 or max_daily_alerts < 1 or candle_minutes <= 0:
        raise ValueError("invalid alert timing parameters")
    seen = set()
    last_alert = None
    day = None
    day_count = 0
    accepted = []
    for s in sorted(signals, key=lambda x: x["bar_index"]):
        idx = s["bar_index"]
        if not isinstance(idx, int) or idx < 0 or idx >= len(bars):
            raise ValueError("invalid signal index")
        if idx in seen:
            raise ValueError("duplicate candidate candle")
        seen.add(idx)
        timestamp = datetime.fromisoformat(
            str(bars[idx]["time"]).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("UTC timestamps required")
        # Market candles are timestamped by their OPEN; a signal becomes
        # actionable only when that candle CLOSES.
        alert_time = timestamp.astimezone(timezone.utc) + timedelta(
            minutes=candle_minutes)
        if day != alert_time.date():
            day, day_count = alert_time.date(), 0
        if last_alert is not None and alert_time-last_alert < timedelta(
                minutes=cooldown_minutes):
            continue
        if day_count >= max_daily_alerts:
            continue
        accepted.append(s)
        last_alert = alert_time
        day_count += 1
    return accepted
