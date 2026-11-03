"""Research dataset coverage and win-rate uncertainty; no live orders."""
from datetime import datetime, timezone
from math import sqrt

def coverage_report(bars, market, target_months=6):
    if market not in ("crypto","forex"):
        raise ValueError("unsupported market")
    if not bars:
        raise ValueError("empty history")
    dates=[datetime.fromisoformat(str(b["time"]).replace("Z","+00:00")) for b in bars]
    if any(d.tzinfo is None for d in dates):
        raise ValueError("timestamps must include timezone")
    if any(b<=a for a,b in zip(dates,dates[1:])):
        raise ValueError("timestamps must be strictly increasing")
    days=(dates[-1]-dates[0]).total_seconds()/86400
    return {"market":market,"candles":len(bars),
            "first_candle_utc":dates[0].astimezone(timezone.utc).isoformat(),
            "last_candle_utc":dates[-1].astimezone(timezone.utc).isoformat(),
            "calendar_span_days":round(days,2),
            "calendar_span_months_approx":round(days/30.44,2),
            "meets_exploratory_coverage_target":days>=target_months*30.44,
            "target_months":target_months,
            "warning":"Calendar coverage is not data completeness or "
                      "proof of profitability. Check missing candles, market "
                      "closures, regimes and point-in-time data."}

def wilson_win_rate_interval(wins, completed_trades, z=1.96):
    """Approximate 95% binomial interval, assuming independent outcomes."""
    if not isinstance(wins,int) or not isinstance(completed_trades,int) or not 0<=wins<=completed_trades:
        raise ValueError("invalid trade counts")
    if completed_trades==0:
        return None
    n=completed_trades
    p=wins/n
    denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return {"lower":round(max(0,center-half),4),
            "upper":round(min(1,center+half),4),
            "warning":"Assumes independent trade outcomes; clustered trades "
                      "and changing regimes may increase uncertainty."}
