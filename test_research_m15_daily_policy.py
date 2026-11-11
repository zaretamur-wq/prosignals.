import unittest
from research_m15_daily_policy import decide_daily_entry as decide

def trade(day, pnl):
    return {"closed_at":day, "net_pnl_usd":pnl}

NOW="2026-11-11T13:00:00+04:00"  # 09:00 UTC
D="2026-11-11T08:00:00Z"

class M15DailyPolicyTests(unittest.TestCase):
    def test_three_wins_halt(self):
        self.assertEqual(decide([trade(D,2)]*3,NOW).reason,"three_wins_completed")
    def test_loss_reduces_risk(self):
        d=decide([trade(D,-1)],NOW)
        self.assertTrue(d.allow)
        self.assertEqual(d.risk_pct,0.5)
    def test_two_losses_halt(self):
        self.assertEqual(decide([trade(D,-1)]*2,NOW).reason,"consecutive_loss_halt")
    def test_realized_loss_halt(self):
        self.assertEqual(decide([trade(D,-6)],NOW).reason,"realized_daily_loss_halt")
    def test_no_forced_entries(self):
        d=decide([],NOW)
        self.assertTrue(d.allow)
        self.assertEqual(d.reason,"eligible_if_signal_and_broker_checks_pass")
    def test_utc_boundary(self):
        # Local 00:30 on Nov 11 is still Nov 10 UTC.
        d=decide([trade("2026-11-10T20:10:00Z",2)]*3,
                 "2026-11-11T00:30:00+04:00")
        self.assertFalse(d.allow)
    def test_previous_utc_day_ignored(self):
        self.assertTrue(decide([trade("2026-11-10T08:00:00Z",-6)],NOW).allow)
    def test_cap(self):
        self.assertEqual(decide([trade(D,0)]*5,NOW).reason,"daily_trade_cap")
    def test_invalid_risk(self):
        with self.assertRaises(ValueError):
            decide([],NOW,initial_risk_pct=4)
    def test_nonfinite(self):
        with self.assertRaises(ValueError):
            decide([trade(D,float("nan"))],NOW)

if __name__=="__main__":
    unittest.main()
