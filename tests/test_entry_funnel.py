"""Research-only entry funnel contract tests."""
import unittest
from research_entry_funnel import entry_funnel_report


class EntryFunnelTests(unittest.TestCase):
    def test_no_signals_distinct_from_rejections(self):
        r = entry_funnel_report("XAUUSD", 2025, 24000, 0, 0)
        self.assertEqual(r["status"], "NO_SIGNALS")
        self.assertEqual(r["rejected_signals"], 0)

    def test_all_rejected_with_categorized_reasons(self):
        r = entry_funnel_report("XAUUSD", 2026, 24000, 8, 0,
                                {"minimum_lot_risk": 6, "spread": 2})
        self.assertEqual(r["status"], "ALL_SIGNALS_REJECTED")
        self.assertEqual(r["rejection_counts"]["minimum_lot_risk"], 6)

    def test_entries_present(self):
        r = entry_funnel_report("EURUSD", 2025, 100, 5, 3,
                                {"session": 1, "margin": 1})
        self.assertEqual(r["status"], "ENTRIES_PRESENT")
        self.assertEqual(r["accepted_entries"], 3)

    def test_missing_bars(self):
        self.assertEqual(entry_funnel_report("AUDUSD", 2026, 0, 0, 0)["status"],
                         "NO_BARS")

    def test_missing_rejection_accounting_rejected(self):
        with self.assertRaises(ValueError):
            entry_funnel_report("XAUUSD", 2025, 10, 5, 2, {"spread": 2})

    def test_bad_counts_and_categories_rejected(self):
        for args in [
            ("EURUSD", 2025, 1, 2, 0, {}),
            ("EURUSD", 2025, 1, 1, 2, {}),
            ("EURUSD", 2025, 1, 1, 0, {"unknown": 1}),
            ("EURUSD", 2025, 1, 1, 0, {"spread": -1}),
            ("EURUSD", 2025, 1, 1, 0, {"spread": True}),
            ("EURUSD", 2025, True, 0, 0, {}),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                entry_funnel_report(*args)


if __name__ == "__main__":
    unittest.main()
