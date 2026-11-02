import tempfile
import unittest
from pathlib import Path
from trade_diagnostics import build_report,save_report
from trade_lifecycle import LifecycleTrade

class DiagnosticsTests(unittest.TestCase):
    def test_match_and_profit_factor(self):
        bars=[
            {"time":"2026-01-01T00:00:00+00:00"},
            {"time":"2026-01-01T00:05:00+00:00"},
            {"time":"2026-01-01T00:10:00+00:00"},
        ]
        signals=[{"bar_index":0,"side":"BUY","score":81},
                 {"bar_index":1,"side":"SELL","score":76}]
        trades=[
            LifecycleTrade("BUY",bars[1]["time"],bars[2]["time"],100,1,2,
                           "TP2",True,104),
            LifecycleTrade("SELL",bars[2]["time"],bars[2]["time"],100,1,-1,
                           "STOP",False,102),
        ]
        report=build_report(bars,signals,trades,100)
        self.assertEqual(report["summary"]["completed_positions"],2)
        self.assertEqual(report["summary"]["completed"]["profit_factor"],2)
        self.assertEqual(report["by_score_bucket"]["80-84"]["count"],1)
        self.assertEqual(report["by_score_bucket"]["75-79"]["count"],1)
        self.assertEqual(report["summary"]["unmatched_positions"],0)
        with tempfile.TemporaryDirectory() as directory:
            csv_file,json_file=save_report(report,directory,"BTC")
            self.assertTrue(Path(csv_file).exists())
            self.assertTrue(Path(json_file).exists())

    def test_unmatched_score_is_not_invented(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"},
              {"time":"2026-01-01T00:05:00+00:00"}]
        trade=LifecycleTrade("BUY",bars[1]["time"],bars[1]["time"],100,1,-2,
                             "STOP",False,98)
        report=build_report(bars,[],[trade],100)
        self.assertIsNone(report["ledger"][0]["signal_score"])
        self.assertEqual(report["summary"]["unmatched_positions"],1)

    def test_end_of_test_not_in_win_rate(self):
        bars=[{"time":"2026-01-01T00:00:00+00:00"},
              {"time":"2026-01-01T00:05:00+00:00"}]
        trade=LifecycleTrade("BUY",bars[1]["time"],bars[1]["time"],100,1,3,
                             "END_OF_TEST",False,103)
        report=build_report(bars,[],[trade],100)
        self.assertEqual(report["summary"]["completed_positions"],0)
        self.assertIsNone(report["summary"]["completed"]["win_rate"])

if __name__=="__main__":
    unittest.main()
