import unittest
from shared_risk import InstrumentSpec, RiskPolicy, size_position
from shared_backtest import run_backtest

class SharedFoundationTests(unittest.TestCase):
    def test_100_dollar_account_rejects_oversized_crypto_order(self):
        q, reason = size_position(100, 100000, 99000,
             InstrumentSpec("BTC", .001, .001), RiskPolicy())
        self.assertEqual(q, 0)
        self.assertIn("minimum",reason)

    def test_forex_position_value(self):
        q, reason = size_position(10000, 1.1, 1.099,
             InstrumentSpec("EURUSD", .01, .01, 100000),
             RiskPolicy(risk_fraction=.01,max_notional_fraction=20))
        self.assertEqual(q,1.0)
        self.assertEqual(reason,"ok")

    def test_daily_loss_kills_new_position(self):
        q, reason = size_position(100,100,99,
             InstrumentSpec("GOLD", .01, .01),
             RiskPolicy(),realized_daily_pnl=-3)
        self.assertEqual(q,0)
        self.assertIn("daily loss",reason)

    def test_stop_first_on_ambiguous_candle(self):
        bars = [dict(time=f"2026-01-01 00:0{i}",open=100,high=100,low=100,close=100)
                for i in range(3)]
        bars[2].update(high=104,low=96)
        trades,equity = run_backtest(bars,
             [dict(bar_index=0,side="BUY",stop=98,target=102)],
             1000,InstrumentSpec("TEST",1,1),
             RiskPolicy(risk_fraction=.01,max_notional_fraction=10))
        self.assertEqual(trades[0].outcome,"STOP")
        self.assertLess(equity,1000)

    def test_next_candle_open_fill(self):
        bars=[dict(time=f"2026-01-01 00:0{i}",open=100+i,
                   high=101+i,low=99+i,close=100+i) for i in range(3)]
        trades,_=run_backtest(bars,[dict(bar_index=0,side="BUY",stop=99,target=105)],
             1000,InstrumentSpec("TEST",1,1),
             RiskPolicy(max_notional_fraction=10))
        self.assertEqual(trades[0].entry,101)

if __name__=="__main__":
    unittest.main()
