import unittest
from research_alert_gates import alert_timing_gate

class AlertTimingTests(unittest.TestCase):
    def test_cooldown_and_daily_cap(self):
        bars=[{"time":f"2026-01-01T{h:02d}:{m:02d}:00+00:00"}
              for h in range(3) for m in range(0,60,5)]
        signals=[{"bar_index":i,"side":"BUY"} for i in range(len(bars))]
        gated=alert_timing_gate(bars,signals,30,3)
        self.assertEqual([x["bar_index"] for x in gated],[0,6,12])

    def test_no_duplicate_candidates(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"}]
        with self.assertRaises(ValueError):
            alert_timing_gate(bars,[{"bar_index":0},{"bar_index":0}])

if __name__=="__main__":
    unittest.main()
