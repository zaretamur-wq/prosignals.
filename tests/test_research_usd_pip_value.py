"""Synthetic arithmetic checks only; no broker validation or backtest."""
import unittest
from research_usd_pip_value import usd_pip_value_per_lot, quote_to_usd_for_usdjpy


class TestResearchUsdPipValue(unittest.TestCase):
    def test_usd_quoted_major_pairs(self):
        for pair in ("EURUSD", "GBPUSD", "AUDUSD"):
            with self.subTest(pair=pair):
                self.assertAlmostEqual(usd_pip_value_per_lot(100000, .0001, 1), 10)

    def test_usdjpy_conversion_is_rate_dependent(self):
        self.assertAlmostEqual(usd_pip_value_per_lot(100000, .01, quote_to_usd_for_usdjpy(150)), 1000/150)
        self.assertAlmostEqual(usd_pip_value_per_lot(100000, .01, quote_to_usd_for_usdjpy(100)), 10)

    def test_gold_requires_explicit_contract_units(self):
        self.assertAlmostEqual(usd_pip_value_per_lot(100, .01, 1), 1)

    def test_invalid_values_fail_closed(self):
        for bad in (0, -1, float("nan"), float("inf"), None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    usd_pip_value_per_lot(100000, .0001, bad)
                with self.assertRaises(ValueError):
                    quote_to_usd_for_usdjpy(bad)


if __name__ == "__main__":
    unittest.main()
