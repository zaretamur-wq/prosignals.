import unittest
from research_costs import cost_sensitivity
from shared_risk import InstrumentSpec

class CostStressTests(unittest.TestCase):
    def test_costs_are_not_beneficial_in_simple_single_trade(self):
        bars=[
            {"time":"2026-01-01T00:00:00+00:00","open":100,"high":100,"low":100,"close":100},
            {"time":"2026-01-01T00:05:00+00:00","open":100,"high":103,"low":100,"close":102},
            {"time":"2026-01-01T00:10:00+00:00","open":103,"high":106,"low":102,"close":105},
        ]
        signals=[{"bar_index":0,"side":"BUY","stop":99,"tp1":101,"tp2":104}]
        results=cost_sensitivity(bars,signals,100,
                 InstrumentSpec("BTC",.000001,.000001),240,.001,.0005)
        self.assertGreaterEqual(results["zero_cost_reference"]["net_pnl"],
                                results["baseline"]["net_pnl"])
        self.assertGreaterEqual(results["baseline"]["net_pnl"],
                                results["double_cost_stress"]["net_pnl"])
        self.assertEqual(results["baseline"]["fee_rate_per_side"],.001)

    def test_negative_fee_rejected(self):
        with self.assertRaises(ValueError):
            cost_sensitivity([],[],100,InstrumentSpec("BTC",.001,.001),
                             240,-.001,0)

if __name__=="__main__":
    unittest.main()
