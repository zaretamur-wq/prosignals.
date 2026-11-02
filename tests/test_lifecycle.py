import unittest
from trade_lifecycle import backtest_lifecycle
from shared_risk import InstrumentSpec, RiskPolicy

SPEC=InstrumentSpec("TEST", .001, .001)
POLICY=RiskPolicy(risk_fraction=.01,max_notional_fraction=10)
def b(i, op=100, hi=100, lo=100, cl=100):
    return {"time":f"2026-01-01T00:{i:02}:00+00:00","open":op,
            "high":hi,"low":lo,"close":cl}
def s():
    return [{"bar_index":0,"side":"BUY","stop":98,"tp1":102,"tp2":104}]
class LifecycleTests(unittest.TestCase):
    def test_stop_first_if_both_touched(self):
        bars=[b(0),b(1),b(2,100,104,97,100)]
        trades,end=backtest_lifecycle(bars,s(),1000,SPEC,POLICY)
        self.assertEqual(trades[0].outcome,"STOP")
        self.assertFalse(trades[0].tp1_hit)
        self.assertLess(end,1000)
    def test_tp1_then_tp2_later(self):
        bars=[b(0),b(1),b(2,100,103,99,102),b(3,103,105,102,104)]
        trades,end=backtest_lifecycle(bars,s(),1000,SPEC,POLICY)
        self.assertEqual(trades[0].outcome,"TP2")
        self.assertTrue(trades[0].tp1_hit)
        self.assertGreater(end,1000)
    def test_tp1_then_breakeven(self):
        bars=[b(0),b(1),b(2,100,103,99,102),b(3,101,102,99,100)]
        trades,end=backtest_lifecycle(bars,s(),1000,SPEC,POLICY)
        self.assertEqual(trades[0].outcome,"BREAKEVEN")
        self.assertTrue(trades[0].tp1_hit)
        self.assertGreater(end,1000)
    def test_expiry(self):
        bars=[b(0),b(1),b(2),b(3),b(4),b(5)]
        trades,end=backtest_lifecycle(bars,s(),1000,SPEC,POLICY,expire_minutes=3)
        self.assertEqual(trades[0].outcome,"EXPIRED")
    def test_next_bar_entry(self):
        bars=[b(0),b(1,101,101,101,101),b(2,101,105,100,104)]
        trades,_=backtest_lifecycle(bars,s(),1000,SPEC,POLICY)
        self.assertEqual(trades[0].entry,101)
    def test_short_tp1_tp2(self):
        signals=[{"bar_index":0,"side":"SELL","stop":102,"tp1":98,"tp2":96}]
        bars=[b(0),b(1),b(2,100,101,97,98),b(3,97,99,95,96)]
        trades,_=backtest_lifecycle(bars,signals,1000,SPEC,POLICY)
        self.assertEqual(trades[0].outcome,"TP2")
    def test_fees_reduce_profits(self):
        bars=[b(0),b(1),b(2,100,103,99,102),b(3,103,105,102,104)]
        _, no_fee = backtest_lifecycle(bars,s(),1000,SPEC,POLICY)
        _, with_fee = backtest_lifecycle(bars,s(),1000,SPEC,POLICY,fee_rate=.001)
        self.assertLess(with_fee,no_fee)

    def test_invalid_fee_is_rejected(self):
        with self.assertRaises(ValueError):
            backtest_lifecycle([b(0),b(1)],s(),1000,SPEC,POLICY,fee_rate=-.1)

    def test_daily_risk_gate(self):
        policy=RiskPolicy(risk_fraction=.01,max_daily_loss_fraction=.001,max_notional_fraction=10)
        # After first loss, second signal cannot enter within same day.
        bars=[b(0),b(1),b(2,100,101,97,98),b(3),b(4),b(5,100,105,99,104)]
        signals=s()+[{"bar_index":3,"side":"BUY","stop":98,"tp1":102,"tp2":104}]
        trades,_=backtest_lifecycle(bars,signals,1000,SPEC,policy)
        self.assertEqual(len(trades),1)
if __name__=="__main__":
    unittest.main()
