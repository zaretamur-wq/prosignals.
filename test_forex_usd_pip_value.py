"""CI-discoverable synthetic checks for pip-value arithmetic only."""
import unittest
from research_usd_pip_value import usd_pip_value_per_lot, quote_to_usd_for_usdjpy


class TestUsdPipValue(unittest.TestCase):
    def test_usd_quote_major_pairs_with_standard_lot_assumptions(self):
        assumptions = {
            "EURUSD": (100000, 0.0001, 1.0),
            "GBPUSD": (100000, 0.0001, 1.0),
            "AUDUSD": (100000, 0.0001, 1.0),
        }
        for symbol, values in assumptions.items():
            with self.subTest(symbol=symbol):
                self.assertAlmostEqual(usd_pip_value_per_lot(*values), 10.0)

    def test_usdjpy_conversion_varies_with_exchange_rate(self):
        self.assertAlmostEqual(usd_pip_value_per_lot(100000, 0.01, quote_to_usd_for_usdjpy(150)), 1000 / 150)
        self.assertAlmostEqual(usd_pip_value_per_lot(100000, 0.01, quote_to_usd_for_usdjpy(100)), 10.0)

    def test_gold_arithmetic_requires_explicit_assumed_contract(self):
        # Synthetic 100-unit contract assumption; not a broker specification.
        self.assertAlmostEqual(usd_pip_value_per_lot(100, 0.01, 1.0), 1.0)

    def test_invalid_conversion_inputs_fail_closed(self):
        for bad in (0, -1, float("nan"), float("inf"), None, True):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    usd_pip_value_per_lot(100000, 0.0001, bad)
                with self.assertRaises(ValueError):
                    quote_to_usd_for_usdjpy(bad)


if __name__ == "__main__":
    unittest.main()
