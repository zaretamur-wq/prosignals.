"""Offline scanner tests; run with python -m unittest test_forex_multi_pair_scanner.py."""
import unittest
import numpy as np
import pandas as pd
from forex_multi_pair_scanner import scan_symbol


def sample(n=250):
    x = 1.08 + np.cumsum(np.random.default_rng(17).normal(0, .0001, n))
    o = np.r_[x[0], x[:-1]]
    return pd.DataFrame({"time": pd.date_range("2025-01-01", periods=n, freq="5min", tz="UTC"),
                         "open": o, "high": np.maximum(o, x) + .0001,
                         "low": np.minimum(o, x) - .0001, "close": x})


class ScannerTests(unittest.TestCase):
    def test_returns_signal_or_none(self):
        r = scan_symbol(sample(), "EURUSD")
        self.assertIn(r["signal"], (None, "BUY", "SELL"))
        self.assertEqual(r["symbol"], "EURUSD")

    def test_rejects_duplicate_timestamps(self):
        d = sample()
        d.loc[3, "time"] = d.loc[2, "time"]
        with self.assertRaises(ValueError):
            scan_symbol(d, "EURUSD")

    def test_rejects_nonfinite_price(self):
        d = sample()
        d.loc[4, "close"] = float("inf")
        with self.assertRaises(ValueError):
            scan_symbol(d, "EURUSD")

    def test_rejects_short_history(self):
        with self.assertRaises(ValueError):
            scan_symbol(sample(100), "EURUSD")

    def test_rejects_unknown_symbol(self):
        with self.assertRaises(ValueError):
            scan_symbol(sample(), "BTCUSD")


if __name__ == "__main__":
    unittest.main()
