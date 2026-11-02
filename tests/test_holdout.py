import unittest
from research_holdout import compare_holdout
from shared_risk import InstrumentSpec

class HoldoutTests(unittest.TestCase):
    def test_split_and_no_signal_crossover(self):
        bars=[{"time":f"2026-01-01T00:{i:02d}:00+00:00",
               "open":100+i,"high":101+i,"low":99+i,"close":100+i}
              for i in range(20)]
        signals=[{"bar_index":12,"side":"BUY","stop":105,"tp1":115,"tp2":120},
                 {"bar_index":13,"side":"BUY","stop":105,"tp1":115,"tp2":120},
                 {"bar_index":14,"side":"BUY","stop":105,"tp1":115,"tp2":120}]
        result=compare_holdout(bars,signals,"crypto",
                InstrumentSpec("BTC",.0001,.0001),100,slippage=.0001)
        self.assertEqual(result["split_index"],14)
        self.assertEqual(result["train"]["all"]["signals"],1)
        self.assertEqual(result["holdout"]["all"]["signals"],1)

    def test_reject_bad_split(self):
        with self.assertRaises(ValueError):
            compare_holdout([],[],"crypto",InstrumentSpec("BTC",.001,.001),100,
                            split_fraction=.1)

if __name__=="__main__":
    unittest.main()
