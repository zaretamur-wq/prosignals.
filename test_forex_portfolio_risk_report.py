"""Tests for offline portfolio risk report."""
import unittest
from forex_portfolio_risk_report import evaluate_portfolio_risk


class PortfolioReportTests(unittest.TestCase):
    def test_two_positions_fit_three_percent(self):
        result = evaluate_portfolio_risk(100, [1, 2])
        self.assertTrue(result["within_risk_budget"])
        self.assertEqual(result["total_planned_risk_usd"], 3)

    def test_combined_risk_exceeds_budget(self):
        result = evaluate_portfolio_risk(100, [2, 2])
        self.assertFalse(result["within_risk_budget"])

    def test_margin_budget(self):
        result = evaluate_portfolio_risk(100, [1, 1], [30, 40], 60)
        self.assertFalse(result["within_margin_budget"])

    def test_margin_length_mismatch(self):
        with self.assertRaises(ValueError):
            evaluate_portfolio_risk(100, [1, 1], [20], 100)

    def test_invalid_nonfinite_risk(self):
        with self.assertRaises(ValueError):
            evaluate_portfolio_risk(100, [float("nan")])

    def test_invalid_equity(self):
        with self.assertRaises(ValueError):
            evaluate_portfolio_risk(0, [1])


if __name__ == "__main__":
    unittest.main()
