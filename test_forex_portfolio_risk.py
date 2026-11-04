"""Offline tests for the shared-account research risk guard."""
import unittest

from forex_portfolio_risk import size_position, can_add_position


class PortfolioRiskTests(unittest.TestCase):
    def test_rejects_minimum_lot_if_risk_too_large(self):
        self.assertEqual(size_position(100, 50, 10), 0.0)

    def test_allows_small_position_within_budget(self):
        self.assertEqual(size_position(100, 10, 10), 0.03)

    def test_margin_restricts_lot_size(self):
        self.assertEqual(size_position(100, 10, 10,
                                       available_margin_usd=10,
                                       margin_usd_per_lot=1000), 0.01)

    def test_insufficient_margin_rejects_trade(self):
        self.assertEqual(size_position(100, 10, 10,
                                       available_margin_usd=5,
                                       margin_usd_per_lot=1000), 0.0)

    def test_costs_reduce_size(self):
        self.assertEqual(size_position(100, 10, 10,
                                       extra_cost_usd_per_lot=50), 0.02)

    def test_combined_exposure_blocks_second_trade(self):
        self.assertFalse(can_add_position(2.5, 1.0, 100))

    def test_combined_exposure_accepts_within_budget(self):
        self.assertTrue(can_add_position(1.0, 2.0, 100))

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            size_position(100, float("nan"), 10)

    def test_missing_margin_parameter_rejected(self):
        with self.assertRaises(ValueError):
            size_position(100, 10, 10, available_margin_usd=50)


if __name__ == "__main__":
    unittest.main()
