"""Tests for research-only instrumented entry event ingestion."""
import unittest
from research_entry_event_ingest import funnel_from_events


class EventIngestTests(unittest.TestCase):
    def test_counts_and_empty_year(self):
        rows = [
            {"symbol": "eurusd", "year": 2025, "event_id": "1",
             "decision": "accepted"},
            {"symbol": "EURUSD", "year": 2025, "event_id": "2",
             "decision": "rejected", "reason": "spread"},
        ]
        out = funnel_from_events(rows, {("EURUSD", 2025): 10,
                                       ("XAUUSD", 2026): 100})
        self.assertEqual(out[0]["status"], "ENTRIES_PRESENT")
        self.assertEqual(out[0]["accepted_entries"], 1)
        self.assertEqual(out[0]["rejection_counts"]["spread"], 1)
        self.assertEqual(out[1]["status"], "NO_SIGNALS")

    def test_duplicate_event_fails(self):
        row = {"symbol": "XAUUSD", "year": 2025, "event_id": "x",
               "decision": "accepted"}
        with self.assertRaises(ValueError):
            funnel_from_events([row, row], {("XAUUSD", 2025): 10})

    def test_unclassified_rejection_fails(self):
        row = {"symbol": "XAUUSD", "year": 2025, "event_id": "x",
               "decision": "rejected"}
        with self.assertRaises(ValueError):
            funnel_from_events([row], {("XAUUSD", 2025): 10})

    def test_event_year_without_bar_count_fails(self):
        row = {"symbol": "XAUUSD", "year": 2025, "event_id": "x",
               "decision": "accepted"}
        with self.assertRaises(ValueError):
            funnel_from_events([row], {})

    def test_events_exceed_bars_fails(self):
        rows = [{"symbol": "XAUUSD", "year": 2025, "event_id": str(i),
                 "decision": "accepted"} for i in range(2)]
        with self.assertRaises(ValueError):
            funnel_from_events(rows, {("XAUUSD", 2025): 1})

    def test_accepted_with_rejection_reason_fails(self):
        row = {"symbol": "XAUUSD", "year": 2025, "event_id": "x",
               "decision": "accepted", "reason": "spread"}
        with self.assertRaises(ValueError):
            funnel_from_events([row], {("XAUUSD", 2025): 10})


if __name__ == "__main__":
    unittest.main()
