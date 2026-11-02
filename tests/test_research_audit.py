import unittest
from research_audit import audit_history

class FidelityAuditTests(unittest.TestCase):
    def test_crypto_gap_detected(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"},
              {"time":"2026-01-01T00:05:00+00:00"},
              {"time":"2026-01-01T00:20:00+00:00"}]
        result=audit_history(bars,"crypto")
        self.assertEqual(result["gap_count"],1)
        self.assertEqual(result["first_gaps"][0]["minutes"],15)
        self.assertFalse(result["ready_for_live"])
        self.assertTrue(result["incomplete_data"])

    def test_contiguous_candles(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"},
              {"time":"2026-01-01T00:05:00+00:00"}]
        self.assertEqual(audit_history(bars,"crypto")["gap_count"],0)

    def test_reject_reversed(self):
        bars=[{"time":"2026-01-01T00:05:00+00:00"},
              {"time":"2026-01-01T00:00:00+00:00"}]
        with self.assertRaises(ValueError):
            audit_history(bars,"crypto")

if __name__=="__main__":
    unittest.main()
