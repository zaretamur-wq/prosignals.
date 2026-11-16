"""Research-only conversion of recorded signal decisions into yearly funnel reports.

Input rows are instrumented strategy events, not inferred from OHLC or order
history. Each row: symbol, year, event_id, decision, reason. decision is
"accepted" or "rejected"; reason must be blank for accepted events.
"""
from collections import defaultdict
from research_entry_funnel import entry_funnel_report, REJECTION_REASONS


def funnel_from_events(events, bars_checked_by_year):
    """Return yearly diagnostics; fail closed on missing/duplicate events."""
    if not isinstance(bars_checked_by_year, dict):
        raise ValueError("bars_checked_by_year must be a mapping")
    groups = defaultdict(list)
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event must be a mapping")
        symbol = event.get("symbol")
        year = event.get("year")
        event_id = event.get("event_id")
        decision = event.get("decision")
        reason = event.get("reason", "")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol required")
        symbol = symbol.strip().upper()
        if type(year) is not int or not 2000 <= year <= 2100:
            raise ValueError("invalid year")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("unique event_id required")
        key = (symbol, year, event_id)
        if key in seen:
            raise ValueError("duplicate signal event")
        seen.add(key)
        if decision not in ("accepted", "rejected"):
            raise ValueError("decision must be accepted or rejected")
        if decision == "accepted" and reason not in ("", None):
            raise ValueError("accepted event cannot have rejection reason")
        if decision == "rejected" and reason not in REJECTION_REASONS:
            raise ValueError("rejected event needs known reason")
        groups[(symbol, year)].append((decision, reason))
    unknown = set(groups) - set(bars_checked_by_year)
    if unknown:
        raise ValueError("event year lacks checked-bar count")
    result = []
    for key, bars in sorted(bars_checked_by_year.items()):
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("bar-count keys must be (symbol, year)")
        symbol, year = key
        rows = groups[key]
        accepted = sum(decision == "accepted" for decision, _ in rows)
        rejected = {}
        for decision, reason in rows:
            if decision == "rejected":
                rejected[reason] = rejected.get(reason, 0) + 1
        result.append(entry_funnel_report(symbol, year, bars, len(rows),
                                          accepted, rejected))
    return result
