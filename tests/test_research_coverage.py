import unittest
from research_coverage import coverage_report, wilson_win_rate_interval

class CoverageTests(unittest.TestCase):
    def test_short_history_not_sufficient(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"},
              {"time":"2026-01-02T00:00:00+00:00"}]
        report=coverage_report(bars,"crypto")
        self.assertFalse(report["meets_exploratory_coverage_target"])
        self.assertEqual(report["calendar_span_days"],1)

    def test_reject_unsorted_history(self):
        with self.assertRaises(ValueError):
            coverage_report([{"time":"2026-01-02T00:00:00+00:00"},
                             {"time":"2026-01-01T00:00:00+00:00"}],"forex")

    def test_uncertainty_interval(self):
        result=wilson_win_rate_interval(8,10)
        self.assertLess(result["lower"],0.8)
        self.assertGreater(result["upper"],0.8)
        self.assertIsNone(wilson_win_rate_interval(0,0))

if __name__=="__main__":
    unittest.main()
