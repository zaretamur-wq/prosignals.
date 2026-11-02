import unittest
from research_forex_sizing import forex_sizing_audit
from shared_risk import InstrumentSpec

class ForexSizingAuditTests(unittest.TestCase):
    def test_minimum_lot_risk_and_notional_reported(self):
        bars=[{"open":1.1},{"open":1.1}]
        signals=[{"bar_index":0,"stop":1.095}]
        spec=InstrumentSpec("EURUSD",.01,.01,100000)
        report=forex_sizing_audit(bars,signals,100,spec)
        self.assertEqual(report["eligible_at_fixed_starting_equity"],0)
        self.assertEqual(report["rejected_at_fixed_starting_equity"],1)
        self.assertAlmostEqual(report["sample_rejections"][0][
            "minimum_order_stop_risk_account_ccy"],5.0)
        self.assertAlmostEqual(report["sample_rejections"][0][
            "minimum_order_notional_account_ccy"],1100.0)

    def test_zero_signals(self):
        report=forex_sizing_audit([{"open":1}],[],100,
                                  InstrumentSpec("EURUSD",.01,.01,100000))
        self.assertEqual(report["candidate_signals"],0)

if __name__=="__main__":
    unittest.main()
