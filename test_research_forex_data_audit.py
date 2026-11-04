"""Tests for conservative Forex data preflight."""
import unittest
import pandas as pd
from research_forex_data_audit import audit_candles

class ForexDataAuditTests(unittest.TestCase):
    def candles(self,n=230):
        return pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="5min",tz="UTC"),
                             "open":[1.1]*n,"high":[1.2]*n,"low":[1.0]*n,"close":[1.1]*n})

    def test_regular_bars(self):
        result=audit_candles(self.candles())
        self.assertTrue(result["data_quality_pass"])
        self.assertEqual(result["nonstandard_interval_count"],0)

    def test_gap_is_flagged_not_filled(self):
        data=self.candles()
        data.loc[120:,"time"]+=pd.Timedelta(minutes=5)
        result=audit_candles(data)
        self.assertEqual(result["nonstandard_interval_count"],1)
        self.assertFalse(result["data_quality_pass"])

    def test_duplicate_time_rejected(self):
        data=self.candles()
        data.loc[10,"time"]=data.loc[9,"time"]
        with self.assertRaises(ValueError):
            audit_candles(data)

    def test_bad_candle_rejected(self):
        data=self.candles()
        data.loc[10,"high"]=0.9
        with self.assertRaises(ValueError):
            audit_candles(data)

    def test_nonfinite_rejected(self):
        data=self.candles()
        data.loc[10,"close"]=float("nan")
        with self.assertRaises(ValueError):
            audit_candles(data)

if __name__=="__main__":
    unittest.main()
