"""Contract tests for research-only minimum-lot stop-distance ceiling."""
import unittest

from shared_risk import InstrumentSpec
from research_min_lot_feasibility import minimum_lot_stop_feasibility


class MinimumLotFeasibilityTests(unittest.TestCase):
    def setUp(self):
        # Illustrative 100 oz/lot Gold contract; must be verified per broker.
        self.gold = InstrumentSpec("XAUUSD", 0.01, 0.01, 100.0)

    def test_gold_100_dollar_3_percent_ceiling_before_costs(self):
        report = minimum_lot_stop_feasibility(100, self.gold)
        self.assertEqual(report["risk_budget_account_ccy"], 3.0)
        self.assertEqual(report["maximum_stop_price_distance"], 3.0)
        self.assertTrue(report["feasible_positive_stop"])
        self.assertFalse(report["margin_verified"])

    def test_adverse_spread_slippage_reduce_ceiling(self):
        report = minimum_lot_stop_feasibility(
            100, self.gold, adverse_spread_price=0.30,
            adverse_slippage_price=0.10)
        self.assertAlmostEqual(report["cost_reserve_account_ccy"], 0.4)
        self.assertAlmostEqual(report["maximum_stop_price_distance"], 2.6)

    def test_round_trip_commission_reduces_ceiling(self):
        spec = InstrumentSpec("XAUUSD", 0.01, 0.01, 100.0,
                              commission_per_unit_per_side=10.0)
        report = minimum_lot_stop_feasibility(100, spec)
        self.assertAlmostEqual(report["maximum_stop_price_distance"], 2.8)

    def test_costs_exceed_budget(self):
        report = minimum_lot_stop_feasibility(
            100, self.gold, adverse_spread_price=4)
        self.assertFalse(report["feasible_positive_stop"])
        self.assertEqual(report["maximum_stop_price_distance"], 0)

    def test_invalid_inputs_rejected(self):
        for value in (-1, 0, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    minimum_lot_stop_feasibility(value, self.gold)
        with self.assertRaises(ValueError):
            minimum_lot_stop_feasibility(100, self.gold,
                                         adverse_spread_price=-0.1)


if __name__ == "__main__":
    unittest.main()
