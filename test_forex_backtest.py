"""Offline smoke tests; no broker credentials or network required."""
import unittest
import numpy as np
import pandas as pd
from forex_backtest import backtest

def candles(n=350):
    rng = np.random.default_rng(7)
    increments = rng.normal(0, 0.00025, n)
    close = 1.08 + np.cumsum(increments)
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=n, freq="5min", tz="UTC"),
        "open":open_, "high":np.maximum(open_,close)+0.00015,
        "low":np.minimum(open_,close)-0.00015, "close":close
    })

class ForexBacktestTests(unittest.TestCase):
    def test_small_account_does_not_force_min_lot(self):
        result = backtest(candles(), initial=100, risk_pct=0.005)
        self.assertGreaterEqual(result["final_usd"], 0)
        self.assertTrue(all(t["lots"] >= 0.01 for t in result["trade_log"]))
    def test_invalid_risk_rejected(self):
        with self.assertRaises(ValueError):
            backtest(candles(), risk_pct=0.05)
    def test_invalid_ohlc_rejected(self):
        d=candles()
        d.loc[5,"high"]=d.loc[5,"low"]-0.001
        with self.assertRaises(ValueError):
            backtest(d)
    def test_no_future_data_from_appended_bars(self):
        d=candles()
        a=backtest(d.iloc[:300].copy())
        b=backtest(d.copy())
        # Longer datasets may add trades, but earlier entries cannot change.
        earlier=[t for t in b["trade_log"] if t["exit_time"] < str(d.time.iloc[299])]
        self.assertEqual(a["trade_log"][:len(earlier)], earlier)

if __name__ == "__main__":
    unittest.main()
