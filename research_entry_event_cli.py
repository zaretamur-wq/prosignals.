"""Research-only CLI for real instrumented entry-event logs.

Usage:
 python research_entry_event_cli.py --events events.json --bars bars.json --output report.json

events.json: [{"symbol":"EURUSD","year":2025,"event_id":"unique","decision":"rejected","reason":"spread"}]
bars.json: [{"symbol":"EURUSD","year":2025,"bars_checked":100}]
No fabricated trades, prices, broker fills, or performance metrics.
"""
import argparse
import json
from pathlib import Path
from research_entry_event_ingest import funnel_from_events


def audit_payload(events, bars):
    if not isinstance(events, list) or not isinstance(bars, list):
        raise ValueError("events and bars must be JSON arrays")
    mapped = {}
    for row in bars:
        if not isinstance(row, dict) or set(row) != {"symbol", "year", "bars_checked"}:
            raise ValueError("each bar row requires symbol, year, bars_checked")
        symbol, year, count = row["symbol"], row["year"], row["bars_checked"]
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("invalid bar symbol")
        if type(year) is not int or not 2000 <= year <= 2100:
            raise ValueError("invalid bar year")
        if type(count) is not int or count < 0:
            raise ValueError("invalid bars_checked")
        key = (symbol.strip().upper(), year)
        if key in mapped:
            raise ValueError("duplicate bar symbol/year")
        mapped[key] = count
    if not mapped:
        raise ValueError("no checked-bar records: cannot audit coverage")
    return funnel_from_events(events, mapped)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--bars", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.events.resolve(), args.bars.resolve()):
        parser.error("output must not overwrite an input")
    events = json.loads(args.events.read_text(encoding="utf-8"))
    bars = json.loads(args.bars.read_text(encoding="utf-8"))
    report = audit_payload(events, bars)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(report)} symbol-year rows; no fills or profitability inferred.")


if __name__ == "__main__":
    main()
