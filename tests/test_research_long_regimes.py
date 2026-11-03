import unittest
import pandas as pd
from research_long_regimes import analyze

class LongRegimeTests(unittest.TestCase):
    def test_chronological_holdout(self):
        times=pd.date_range("2020-01-01",periods=250,freq="D",tz="UTC")
        df=pd.DataFrame({"time":times,"close":[100+i*.1 for i in range(250)]})
        result=analyze(df,lookback=20,horizon=5)
        self.assertLess(result["segments"]["development"]["end_utc"],
                        result["segments"]["holdout"]["start_utc"])
        self.assertEqual(result["bars"],250)

    def test_short_history_rejected(self):
        df=pd.DataFrame({"time":["2020-01-01","2020-01-02"],"close":[1,2]})
        with self.assertRaises(ValueError):
            analyze(df)

if __name__=="__main__":
    unittest.main()
