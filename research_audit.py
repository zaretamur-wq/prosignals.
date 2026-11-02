"""Research audit: disclose fidelity gaps and candle continuity.

This is an evidence checklist, not a strategy score or a claim of accuracy.
"""
from datetime import datetime, timezone

def audit_history(bars, market, expected_minutes=None):
    if market not in ("crypto","forex"):
        raise ValueError("unknown market")
    if expected_minutes is None:
        expected_minutes=5 if market=="crypto" else 60
    if expected_minutes<=0:
        raise ValueError("invalid interval")
    gaps=[]
    prev=None
    for i,bar in enumerate(bars):
        ts=datetime.fromisoformat(str(bar["time"]).replace("Z","+00:00"))
        if ts.tzinfo is None:
            raise ValueError("timestamps must include timezone")
        ts=ts.astimezone(timezone.utc)
        if prev is not None:
            minutes=(ts-prev).total_seconds()/60
            if minutes<=0:
                raise ValueError("candles must be strictly chronological")
            if minutes>expected_minutes*1.01:
                gaps.append({"after_index":i-1,"before_index":i,
                             "minutes":round(minutes,3)})
        prev=ts
    shared_missing=[
        "Actual bid/ask spread and order-book liquidity",
        "Broker/exchange fill latency and rejected orders",
        "Historical Telegram delivery, polling and live state",
        "Independent out-of-sample forward paper trading",
    ]
    crypto_missing=[
        "Point-in-time funding, open interest and order-book imbalance",
        "Point-in-time economic news/calendar blocks",
        "BTC cross-asset filter for altcoin signals",
        "Live open-signal suppression and multi-asset exposure",
    ]
    forex_missing=[
        "Broker-specific leverage, margin and contract sizes",
        "Broker-specific swap, spread and financing costs",
    ]
    return {
        "candles":len(bars),
        "expected_interval_minutes":expected_minutes,
        "gap_count":len(gaps),
        "first_gaps":gaps[:10],
        "incomplete_data":bool(gaps),
        "unverified_fidelity":shared_missing+(
            crypto_missing if market=="crypto" else forex_missing),
        "ready_for_live":False,
        "warning":"Data gaps can change signals and next-bar fills. "
                  "Historical results are exploratory until fidelity gaps are resolved."
    }
