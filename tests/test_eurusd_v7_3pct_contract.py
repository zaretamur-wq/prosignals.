"""Static, research-only safety contract for EURUSD M15 v7.

These tests inspect source configuration and invariants; they do NOT compile MQL5,
execute orders, or establish profitability or broker-fill correctness.
"""
from pathlib import Path
import re
import unittest

EA = Path(__file__).resolve().parents[1] / "ProSignals_EURUSD_M15_H1_Pullback_Research_v7_3pct.mq5"


class EURUSDV7ResearchContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = EA.read_text(encoding="utf-8")

    def test_default_execution_off_and_demo_guard(self):
        self.assertRegex(self.source, r"InpEnableDemoOrders\s*=\s*false\s*;")
        self.assertIn("ACCOUNT_TRADE_MODE_DEMO", self.source)
        self.assertIn("MQLInfoInteger(MQL_TESTER)", self.source)
        self.assertIn('_Symbol!="EURUSD"||_Period!=PERIOD_M15', self.source)

    def test_fixed_three_percent_risk_cap_and_no_loss_escalation(self):
        self.assertRegex(self.source, r"InpRiskPct\s*=\s*3\.0\s*;")
        self.assertIn("InpRiskPct>3.0", self.source)
        self.assertIn("MathMin(InpResearchCapitalUSD,AccountInfoDouble(ACCOUNT_EQUITY))", self.source)
        self.assertIn("double budget=cappedEquity*riskPct/100.0", self.source)
        self.assertNotIn("InpReducedRiskPct", self.source)
        self.assertIn("if(lots+1e-9<minimum)return 0;", self.source)

    def test_two_r_target_and_post_fill_audit(self):
        self.assertRegex(self.source, r"InpRewardR\s*=\s*2\.0\s*;")
        self.assertIn("MathAbs(InpRewardR-2.0)>1e-8", self.source)
        self.assertIn("AuditExecutedRiskAndRR(budget)", self.source)
        self.assertIn("OrderCalcProfit(order,_Symbol,volume,openPrice,stop,stopCash)", self.source)
        self.assertIn("trade.PositionModify(ticket,stop,expectedTarget)", self.source)

    def test_daily_guardrails(self):
        self.assertRegex(self.source, r"InpMaxDailyLossUSD\s*=\s*6\.0\s*;")
        self.assertRegex(self.source, r"InpMaxEntriesPerDay\s*=\s*3\s*;")
        self.assertRegex(self.source, r"InpMaxConsecutiveLosses\s*=\s*2\s*;")
        self.assertIn("realized<=-InpMaxDailyLossUSD", self.source)
        self.assertIn("streak>=InpMaxConsecutiveLosses", self.source)
        self.assertIn("PositionSelect(_Symbol)", self.source)

    def test_example_win_rate_does_not_equal_observed_profit(self):
        # Illustrative fixed-R arithmetic only; not historical strategy results.
        wins, losses, reward_r = 53, 47, 2
        gross_r = wins * reward_r - losses
        self.assertEqual(gross_r, 59)
        # Even positive gross R requires realistic execution and cost validation.
        self.assertGreater(gross_r, 0)


if __name__ == "__main__":
    unittest.main()
