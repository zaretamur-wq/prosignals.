import unittest
from research_acceptance import assess_trades

class AcceptanceTests(unittest.TestCase):
    def test_high_win_rate_still_fails_if_unprofitable(self):
        report=assess_trades([0.001]*8+[-0.1]*2,min_trades=10)
        self.assertEqual(report["win_rate"],0.8)
        self.assertFalse(report["research_gate_passed"])
        self.assertFalse(report["checks"]["positive_net_return"])

    def test_insufficient_sample_rejected(self):
        report=assess_trades([0.03,-0.01,0.03],min_trades=100)
        self.assertFalse(report["checks"]["enough_trades"])

    def test_invalid_loss_rejected(self):
        with self.assertRaises(ValueError):
            assess_trades([-1])

if __name__=="__main__":
    unittest.main()
