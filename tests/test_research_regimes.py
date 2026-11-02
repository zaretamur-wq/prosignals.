import unittest
from research_regimes import regimes, regime_filter

class RegimeTests(unittest.TestCase):
    def test_no_future_candle_leakage(self):
        prices=[100+i for i in range(12)]
        a=regimes([{"close":v} for v in prices],lookback=3,
                  trend_threshold=.001,volatility_floor=0)
        changed=prices+[1_000_000]
        b=regimes([{"close":v} for v in changed],lookback=3,
                  trend_threshold=.001,volatility_floor=0)
        self.assertEqual(a,b[:len(a)])
        self.assertIsNone(a[2])
        self.assertEqual(a[3]["trend"],"UP")

    def test_directional_gate(self):
        bars=[{"close":100+i} for i in range(12)]
        rs=regimes(bars,lookback=3,trend_threshold=.001,volatility_floor=0)
        signals=[{"bar_index":5,"side":"BUY"},
                 {"bar_index":6,"side":"SELL"}]
        self.assertEqual(len(regime_filter(signals,rs,"all")),2)
        self.assertEqual(len(regime_filter(signals,rs,"trend")),1)
        self.assertEqual(len(regime_filter(signals,rs,"trend_and_volatility")),1)

    def test_invalid_regime(self):
        with self.assertRaises(ValueError):
            regime_filter([],[],"future_peeking")

if __name__=="__main__":
    unittest.main()
