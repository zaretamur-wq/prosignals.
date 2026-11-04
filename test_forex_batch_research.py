"""Research-only tests for independent multi-symbol batch runner."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forex_batch_research import run_independent_backtests


class BatchResearchTests(unittest.TestCase):
    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            run_independent_backtests({})

    def test_rejects_unverified_pip_value(self):
        with self.assertRaises(ValueError):
            run_independent_backtests({"XAUUSD": "unused.csv"})

    def test_keeps_symbols_independent(self):
        with patch("forex_batch_research.pd.read_csv", return_value="candles") as read:
            with patch("forex_batch_research.backtest", side_effect=[
                {"symbol": "EURUSD", "final_usd": 105},
                {"symbol": "GBPUSD", "final_usd": 95},
            ]) as bt:
                result = run_independent_backtests({"EURUSD": "e.csv", "GBPUSD": "g.csv"}, initial=100)
        self.assertEqual(result["mode"], "independent_per_symbol_not_portfolio")
        self.assertEqual(result["results"]["EURUSD"]["final_usd"], 105)
        self.assertEqual(result["results"]["GBPUSD"]["final_usd"], 95)
        self.assertNotIn("portfolio_final_usd", result)
        self.assertEqual(bt.call_count, 2)
        self.assertEqual(read.call_count, 2)


if __name__ == "__main__":
    unittest.main()
