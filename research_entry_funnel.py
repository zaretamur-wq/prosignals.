"""Research-only funnel audit of candidate signals and entry rejections.

Use counts from the SAME symbol, year, and tested strategy. This module does not
infer rejection reasons from absence of trades and never places orders.
"""
from collections import Counter

REJECTION_REASONS = frozenset({
    "spread", "minimum_lot_risk", "margin", "stop_level",
    "session", "daily_loss_halt", "daily_entry_limit",
    "cooldown", "broker_reject", "other",
})


def entry_funnel_report(symbol, year, bars_checked, signals_found,
                        accepted_entries, rejection_counts=None):
    """Validate accounting and return a transparent diagnostic.

    One candidate signal must resolve into exactly one accepted entry or
    one classified rejection. Count skipped bars separately, not as rejections.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol required")
    if type(year) is not int or not 2000 <= year <= 2100:
        raise ValueError("invalid calendar year")
    counts = (bars_checked, signals_found, accepted_entries)
    if any(type(x) is not int or x < 0 for x in counts):
        raise ValueError("counts must be nonnegative integers")
    if not accepted_entries <= signals_found <= bars_checked:
        raise ValueError("entries cannot exceed signals or checked bars")
    if rejection_counts is None:
        rejection_counts = {}
    if not isinstance(rejection_counts, dict):
        raise ValueError("rejection_counts must be a mapping")
    if set(rejection_counts) - REJECTION_REASONS:
        raise ValueError("unknown rejection category")
    if any(type(v) is not int or v < 0 for v in rejection_counts.values()):
        raise ValueError("invalid rejection count")
    rejected = sum(rejection_counts.values())
    if rejected + accepted_entries != signals_found:
        raise ValueError("every signal must be accounted for exactly once")
    if bars_checked == 0:
        status = "NO_BARS"
    elif signals_found == 0:
        status = "NO_SIGNALS"
    elif accepted_entries == 0:
        status = "ALL_SIGNALS_REJECTED"
    else:
        status = "ENTRIES_PRESENT"
    return {
        "symbol": symbol.strip().upper(), "year": year,
        "bars_checked": bars_checked, "signals_found": signals_found,
        "accepted_entries": accepted_entries, "rejected_signals": rejected,
        "rejection_counts": {k: rejection_counts.get(k, 0)
                             for k in sorted(REJECTION_REASONS)},
        "status": status,
        "note": "Diagnostic counts only; requires instrumented strategy logs. "
                "Does not establish profitability, fills, or broker margin."
    }
