"""Research-only regression checks for backtester rejection diagnostics.

Run with: python -m unittest discover -p 'test_forex*.py' -v
Synthetic prices are NOT evidence of profitability.
"""
import unittest
import numpy as np
import pandas as pd
from forex_backtest import backtest


def candles(n=260):
    times = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    prices = np.full(n, 1.1000)
    return pd.DataFrame({
        "time": times, "open": prices, "high": prices + 0.0002,
        "low": prices - 0.0002, "close": prices
    })


class ForexDiagnosticRegressionTests(unittest.TestCase):
    def test_flat_market_has_no_entries(self):
        result = backtest(candles())
        d = result["signal_diagnostics"]
        self.assertEqual(result["trades"], 0)
        self.assertIsNone(result["win_rate_pct"])
        self.assertEqual(d["accepted_entries"], 0)
        self.assertEqual(d["min_lot_rejections"], 0)
        self.assertGreater(d["no_signal_bars"], 0)
        self.assertEqual(len(result["trade_log"]), 0)

    def test_unsupported_symbols_fail_closed(self):
        for symbol in ("USDJPY", "AUDUSD", "XAUUSD"):
            with self.subTest(symbol=symbol):
                with self.assertRaisesRegex(ValueError, "Only EURUSD and GBPUSD"):
                    backtest(candles(), symbol=symbol)

    def test_invalid_spread_rejected(self):
        with self.assertRaises(ValueError):
            backtest(candles(), spread_pips=-0.1)

    def test_invalid_ohlc_rejected(self):
        data = candles()
        data.loc[0, "high"] = 1.0
        with self.assertRaisesRegex(ValueError, "Invalid OHLC"):
            backtest(data)

    def test_risk_above_three_percent_rejected(self):
        with self.assertRaises(ValueError):
            backtest(candles(), risk_pct=0.031)


if __name__ == "__main__":
    unittest.main()
