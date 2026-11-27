"""Offline tests for Yahoo Forex symbol mapping and XM research settings."""
import unittest
from unittest.mock import patch

import pandas as pd

from research_data import forex_yahoo
from research_xm_standard_forex import PIP, SPREAD_PIPS, RISK_SCENARIOS, usd_value


def sample_yahoo_history():
    index = pd.date_range("2024-01-01", periods=1000, freq="h", tz="UTC")
    frame = pd.DataFrame({
        "Open": [1.10] * len(index),
        "High": [1.11] * len(index),
        "Low": [1.09] * len(index),
        "Close": [1.105] * len(index),
    }, index=index)
    frame.index.name = "Datetime"
    return frame


class ForexDataPipelineTests(unittest.TestCase):
    @patch("research_data.yf.download")
    def test_all_supported_forex_symbols_use_two_year_hourly_default(self, download):
        tickers = {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "AUDUSD": "AUDUSD=X",
            "USDJPY": "JPY=X",
            "GOLD": "GC=F",
        }
        download.side_effect = lambda *args, **kwargs: sample_yahoo_history()
        for symbol, ticker in tickers.items():
            with self.subTest(symbol=symbol):
                result = forex_yahoo(symbol)
                self.assertEqual(download.call_args.args[0], ticker)
                self.assertEqual(download.call_args.kwargs["period"], "2y")
                self.assertEqual(download.call_args.kwargs["interval"], "1h")
                self.assertGreaterEqual(len(result), 852)
                self.assertEqual(set(result.columns), {"time", "open", "high", "low", "close"})

    @patch("research_data.yf.download")
    def test_custom_yahoo_period_is_passed_through(self, download):
        download.return_value = sample_yahoo_history()
        forex_yahoo("EURUSD", period="6mo")
        self.assertEqual(download.call_args.kwargs["period"], "6mo")

    @patch("research_data.yf.download")
    def test_unknown_symbol_fails_without_network_call(self, download):
        with self.assertRaises(ValueError):
            forex_yahoo("FAKE")
        download.assert_not_called()

    def test_audusd_is_supported_in_xm_model_and_three_percent_risk_scenario(self):
        self.assertEqual(PIP["AUDUSD"], 0.0001)
        self.assertEqual(SPREAD_PIPS["AUDUSD"], 2.0)
        self.assertEqual(usd_value("AUDUSD", 1.5, 1000), 1000)
        self.assertIn(0.03, RISK_SCENARIOS)


if __name__ == "__main__":
    unittest.main()
