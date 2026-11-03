import unittest
from shared_risk import InstrumentSpec
from research_margin import MarginScenario
from research_margin_backtest import backtest_margin_scenario

class MarginBacktestTests(unittest.TestCase):
    def test_uses_margin_sizing_without_live_orders(self):
        bars=[
            dict(time="2026-01-01T00:00:00Z",open=1.1,high=1.1,low=1.1,close=1.1),
            dict(time="2026-01-01T01:00:00Z",open=1.1,high=1.1,low=1.1,close=1.1),
            dict(time="2026-01-01T02:00:00Z",open=1.1,high=1.102,low=1.1,close=1.102)]
        signals=[dict(bar_index=0,side="BUY",stop=1.0998,target=1.101)]
        spec=InstrumentSpec("EURUSD",.01,.01,100000)
        report=backtest_margin_scenario(bars,signals,100,spec,MarginScenario(30))
        self.assertEqual(report["completed_trades"],1)
        self.assertGreater(report["net_pnl"],0)

    def test_rejects_unmodeled_spread(self):
        with self.assertRaises(ValueError):
            backtest_margin_scenario([],[],100,InstrumentSpec("EURUSD",.01,.01,100000),
                                     MarginScenario(30,spread_price=.0001))
if __name__=="__main__":
    unittest.main()
