"""Integration tests for the offline chronological Forex evaluation pipeline."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from forex_chronological_evaluation import evaluate

class ForexChronologicalEvaluationTests(unittest.TestCase):
    def make_csv(self, directory, count=3000):
        path=Path(directory)/"eurusd.csv"
        pd.DataFrame({
            "time":pd.date_range("2026-01-01",periods=count,freq="5min",tz="UTC"),
            "open":[1.10]*count,"high":[1.11]*count,
            "low":[1.09]*count,"close":[1.10]*count
        }).to_csv(path,index=False)
        return path

    def test_partitioned_baseline_runs_and_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            source=self.make_csv(directory)
            fake={"trades":0,"win_rate_pct":None,"final_usd":100.0,"trade_log":[]}
            with patch("forex_chronological_evaluation.backtest",return_value=fake) as runner:
                report=evaluate(source,"EURUSD")
            self.assertEqual(runner.call_count,3)
            self.assertEqual(set(report["results"]),{"train","validation","test"})
            self.assertEqual(len(report["source_sha256"]),64)
            self.assertEqual(report["quality"]["rows"],3000)
            self.assertEqual([len(call.args[0]) for call in runner.call_args_list],
                             [1800,399,399])
            self.assertEqual(report["status"],"research_only_not_broker_verified")

    def test_insufficient_bars_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source=self.make_csv(directory,2999)
            with self.assertRaisesRegex(ValueError,"3000"):
                evaluate(source,"EURUSD")

    def test_duplicate_time_rejected_before_backtest(self):
        with tempfile.TemporaryDirectory() as directory:
            source=self.make_csv(directory)
            frame=pd.read_csv(source)
            frame.loc[1,"time"]=frame.loc[0,"time"]
            frame.to_csv(source,index=False)
            with patch("forex_chronological_evaluation.backtest") as runner:
                with self.assertRaises(ValueError):
                    evaluate(source,"EURUSD")
                runner.assert_not_called()

if __name__=="__main__":
    unittest.main()
