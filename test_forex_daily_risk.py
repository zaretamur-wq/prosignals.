"""Unit tests for UTC daily risk gate. Run: python -m unittest test_forex_daily_risk.py"""
import unittest
import math
from forex_daily_risk import DailyRiskGuard


class DailyRiskGuardTests(unittest.TestCase):
    def test_profit_halt(self):
        guard = DailyRiskGuard()
        self.assertTrue(guard.can_open("2026-11-04T09:00:00+00:00"))
        guard.record_exit("2026-11-04T09:30:00+00:00", 15)
        self.assertFalse(guard.can_open("2026-11-04T10:00:00+00:00"))
        self.assertTrue(guard.can_open("2026-11-05T00:00:00+00:00"))

    def test_loss_halt(self):
        guard = DailyRiskGuard()
        guard.record_exit("2026-11-04T09:00:00+00:00", -3)
        self.assertTrue(guard.can_open("2026-11-04T09:30:00+00:00"))
        guard.record_exit("2026-11-04T10:00:00+00:00", -3)
        self.assertFalse(guard.can_open("2026-11-04T10:30:00+00:00"))

    def test_timezone_conversion(self):
        guard = DailyRiskGuard()
        guard.record_exit("2026-11-05T01:00:00+04:00", 15)
        self.assertFalse(guard.can_open("2026-11-04T22:00:00+00:00"))

    def test_nonfinite_limits_rejected(self):
        for bad in (float("nan"), float("inf"), -1.0, 0.0):
            with self.assertRaises(ValueError):
                DailyRiskGuard(profit_target_usd=bad)
            with self.assertRaises(ValueError):
                DailyRiskGuard(loss_limit_usd=bad)

    def test_nonfinite_pnl_rejected(self):
        guard = DailyRiskGuard()
        for bad in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValueError):
                guard.record_exit("2026-11-04T09:00:00+00:00", bad)
        self.assertEqual(guard.summary(), {})

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            DailyRiskGuard().can_open("2026-11-04T09:00:00")


if __name__ == "__main__":
    unittest.main()
