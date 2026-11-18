"""Offline regression tests for research_entry_event_cli (no MT5 connection)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from research_entry_event_cli import audit_payload


class AuditPayloadTests(unittest.TestCase):
    def test_no_signal_year_preserved(self):
        self.assertEqual(audit_payload([], [{"symbol":"XAUUSD","year":2026,"bars_checked":400}])[0]["status"], "NO_SIGNALS")

    def test_rejection_classified_without_inferred_fills(self):
        result = audit_payload([{"symbol":"eurusd","year":2025,"event_id":"a","decision":"rejected","reason":"spread"}],
                               [{"symbol":"EURUSD","year":2025,"bars_checked":10}])
        self.assertEqual(result[0]["status"], "ALL_SIGNALS_REJECTED")
        self.assertEqual(result[0]["rejection_counts"]["spread"], 1)

    def test_duplicate_normalized_bar_keys_rejected(self):
        with self.assertRaises(ValueError):
            audit_payload([], [{"symbol":"EURUSD","year":2025,"bars_checked":1},
                               {"symbol":"eurusd","year":2025,"bars_checked":1}])

    def test_missing_coverage_rejected(self):
        with self.assertRaises(ValueError):
            audit_payload([], [])

    def test_boolean_year_and_count_rejected(self):
        for bad in [{"symbol":"EURUSD","year":True,"bars_checked":1},
                    {"symbol":"EURUSD","year":2025,"bars_checked":True}]:
            with self.assertRaises(ValueError):
                audit_payload([], [bad])

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            events, bars, out = (folder / name for name in ("events.json", "bars.json", "report.json"))
            events.write_text("[]", encoding="utf-8")
            bars.write_text(json.dumps([{"symbol":"AUDUSD","year":2026,"bars_checked":200}]), encoding="utf-8")
            script = Path(__file__).with_name("research_entry_event_cli.py")
            result = subprocess.run([sys.executable, str(script), "--events", str(events),
                                     "--bars", str(bars), "--output", str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text())[0]["status"], "NO_SIGNALS")


if __name__ == "__main__":
    unittest.main()
