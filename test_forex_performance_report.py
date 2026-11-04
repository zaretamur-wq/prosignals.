"""Regression tests for closed-trade performance metrics."""
import unittest
from forex_performance_report import summarize

class ForexPerformanceReportTests(unittest.TestCase):
    def test_mixed_trades(self):
        report=summarize([{"pnl_usd":10},{"pnl_usd":-5},{"pnl_usd":2},{"pnl_usd":-3}],100)
        self.assertEqual(report["completed_trades"],4)
        self.assertEqual(report["win_rate_pct"],50.0)
        self.assertEqual(report["profit_factor"],1.5)
        self.assertEqual(report["net_pnl_usd"],4.0)
        self.assertGreater(report["max_closed_trade_drawdown_pct"],0)

    def test_no_trades_does_not_claim_win_rate(self):
        report=summarize([])
        self.assertIsNone(report["win_rate_pct"])
        self.assertIsNone(report["profit_factor"])

    def test_all_wins_has_undefined_profit_factor(self):
        report=summarize([{"pnl_usd":3}])
        self.assertIsNone(report["profit_factor"])
        self.assertEqual(report["win_rate_pct"],100.0)

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            summarize([{"pnl_usd":float("nan")}])

if __name__=="__main__":
    unittest.main()
