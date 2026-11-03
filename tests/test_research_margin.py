import unittest
from research_margin import MarginScenario, margin_position_size, compare_margin_scenarios
from shared_risk import InstrumentSpec, RiskPolicy

class MarginResearchTests(unittest.TestCase):
    def setUp(self):
        self.fx=InstrumentSpec("EURUSD",0.01,0.01,100000)

    def test_risk_budget_blocks_minimum_lot_even_with_leverage(self):
        qty,reason,diag=margin_position_size(
            100,1.1,1.095,self.fx,MarginScenario(leverage=100))
        self.assertEqual(qty,0)
        self.assertGreater(diag["minimum_lot_stop_risk"],diag["risk_budget"])

    def test_scenario_can_allow_minimum_lot_without_changing_risk_limit(self):
        qty,reason,diag=margin_position_size(
            1000,1.1,1.0995,self.fx,MarginScenario(leverage=100))
        self.assertGreaterEqual(qty,0.01)
        self.assertLessEqual(qty*diag["minimum_lot_stop_risk"]/0.01,
                             diag["risk_budget"]+0.00001)

    def test_spread_reduces_position_size(self):
        a=margin_position_size(1000,1.1,1.0995,self.fx,
                               MarginScenario(leverage=100))[0]
        b=margin_position_size(1000,1.1,1.0995,self.fx,
                               MarginScenario(leverage=100,spread_price=.0002))[0]
        self.assertLessEqual(b,a)

    def test_scenario_comparison_counts_candidates(self):
        bars=[{"open":1.1},{"open":1.1}]
        signals=[{"bar_index":0,"stop":1.0995}]
        result=compare_margin_scenarios(bars,signals,1000,self.fx)
        self.assertEqual(set(result["hypothetical_leverage_scenarios"]),
                         {"1","10","30","100"})
        for item in result["hypothetical_leverage_scenarios"].values():
            self.assertEqual(item["candidate_signals"],1)
            self.assertEqual(item["sizing_eligible_signals"]+
                             sum(item["rejection_reasons"].values()),1)

    def test_invalid_leverage_rejected(self):
        qty,reason,_=margin_position_size(
            100,1.1,1.09,self.fx,MarginScenario(leverage=0))
        self.assertEqual(qty,0)
        self.assertEqual(reason,"invalid configuration")

if __name__=="__main__":
    unittest.main()
