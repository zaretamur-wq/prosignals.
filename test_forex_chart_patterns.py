import unittest
import pandas as pd
from forex_chart_patterns import detect

class ChartPatterns(unittest.TestCase):
    def setUp(self):
        self.df=pd.DataFrame([{"open":1.10,"high":1.11,"low":1.09,"close":1.10} for _ in range(45)])
    def test_no_lookahead(self):
        self.df.loc[40]=[1.10,1.115,1.095,1.105]
        a=detect(self.df,40)
        self.df.loc[41]=[1.10,9.0,0.1,1.10]
        self.assertEqual(a,detect(self.df,40))
    def test_sweep_high(self):
        self.df.loc[40]=[1.105,1.12,1.095,1.10]
        self.assertEqual(detect(self.df,40)["pattern"],"failed_breakout_high")
    def test_breakout(self):
        self.df.loc[40]=[1.105,1.13,1.10,1.12]
        self.assertEqual(detect(self.df,40)["side"],"BUY")
    def test_no_signal_flat(self):
        self.assertIsNone(detect(self.df,40))
if __name__=="__main__": unittest.main()
