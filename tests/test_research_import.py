import tempfile
import unittest
from pathlib import Path
from research_import import validate_history_csv

class ImportValidationTests(unittest.TestCase):
    def make_csv(self, rows):
        tmp=tempfile.TemporaryDirectory()
        p=Path(tmp.name)/"bars.csv"
        p.write_text("time,open,high,low,close,vol\n"+rows,encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return p

    def test_crypto_valid_complete_bars(self):
        p=self.make_csv("2026-01-01T00:00:00Z,1,2,1,2,10\n"
                        "2026-01-01T00:05:00Z,2,3,2,3,11\n")
        result=validate_history_csv(p,"crypto","5m",min_days=0)
        self.assertTrue(result["ready_for_research"])
        self.assertEqual(result["missing_candle_slots"],0)

    def test_crypto_gap_is_not_ready(self):
        p=self.make_csv("2026-01-01T00:00:00Z,1,2,1,2,10\n"
                        "2026-01-01T00:10:00Z,2,3,2,3,11\n")
        result=validate_history_csv(p,"crypto","5m",min_days=0)
        self.assertFalse(result["ready_for_research"])
        self.assertEqual(result["missing_candle_slots"],1)

    def test_bad_ohlc_rejected(self):
        p=self.make_csv("2026-01-01T00:00:00Z,1,1,2,1,10\n"
                        "2026-01-01T00:05:00Z,1,2,1,2,10\n")
        with self.assertRaises(ValueError):
            validate_history_csv(p,"crypto","5m",min_days=0)

if __name__=="__main__":
    unittest.main()
