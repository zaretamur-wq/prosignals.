"""Reproducible research comparison safeguards (no broker orders)."""
import unittest
from unittest.mock import patch
import pandas as pd
from research_video_comparison import evaluate

def sample():
    n=1200
    return pd.DataFrame({"time":pd.date_range("2026-01-05 05:00",periods=n,freq="5min",tz="UTC"),
        "open":[1.1000]*n,"high":[1.1005]*n,"low":[1.0995]*n,"close":[1.1000]*n})

class ComparisonTests(unittest.TestCase):
    def test_fixed_1r_and_2r_in_both_periods(self):
        df=sample()
        with patch("research_video_comparison.run",return_value={"trades":0}) as engine:
            report=evaluate(df)
        self.assertEqual(len(report["strategies"]),2)
        self.assertEqual(engine.call_count,8)
        self.assertEqual({v["signal_count"] for v in report["strategies"].values()},{0})
        self.assertTrue(all("holdout" in x["2R"] for x in report["strategies"].values()))

    def test_refuses_nonchronological(self):
        df=sample()
        df.loc[10,"time"]=df.loc[9,"time"]
        with self.assertRaises(ValueError):
            evaluate(df)

    def test_refuses_invalid_risk(self):
        with self.assertRaises(ValueError):
            evaluate(sample(),risk_fraction=.04)

if __name__=="__main__":unittest.main()
