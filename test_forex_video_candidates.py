"""Regression checks for research-only video candidate signals."""
import unittest
import pandas as pd
from research_video_candidates import twenty_bar_sweep, ny_first_four_hour_reentry

def candles(start, n, base=1.1000):
    return pd.DataFrame({
      "time":pd.date_range(start,periods=n,freq="5min",tz="UTC"),
      "open":[base]*n,"high":[base+0.001]*n,
      "low":[base-0.001]*n,"close":[base]*n,
    })

class VideoCandidateTests(unittest.TestCase):
    def test_sweep_requires_depth_and_recovery(self):
        df=candles("2026-01-05 00:00",60)
        df.loc[25,"low"]=1.094
        df.loc[25,"close"]=1.0995
        matches=twenty_bar_sweep(df)
        self.assertEqual([x["bar_index"] for x in matches],[25])
        self.assertEqual(matches[0]["side"],"BUY")
        self.assertEqual(matches[0]["stop"],1.094)

    def test_ny_range_needs_breakout_then_later_reentry(self):
        # New York is UTC-5 in January, so midnight is 05:00 UTC.
        df=candles("2026-01-05 05:00",80)
        df.loc[48,"close"]=1.1020;df.loc[48,"high"]=1.1030
        df.loc[49,"close"]=1.1000
        signals=ny_first_four_hour_reentry(df)
        self.assertEqual(len(signals),1)
        self.assertEqual(signals[0]["bar_index"],49)
        self.assertEqual(signals[0]["side"],"SELL")
        self.assertEqual(signals[0]["stop"],1.103)

    def test_no_signal_without_complete_ny_range(self):
        df=candles("2026-01-05 06:00",65)
        df.loc[47,"close"]=1.102;df.loc[48,"close"]=1.100
        self.assertEqual(ny_first_four_hour_reentry(df),[])

    def test_ny_summer_dst_boundaries(self):
        # NY midnight is UTC-4 in July, so range begins at 04:00 UTC.
        df=candles("2026-07-06 04:00",60)
        df.loc[48,"close"]=1.097;df.loc[48,"low"]=1.096
        df.loc[49,"close"]=1.100
        signals=ny_first_four_hour_reentry(df)
        self.assertEqual([(x["bar_index"],x["side"]) for x in signals],[(49,"BUY")])
        self.assertEqual(signals[0]["stop"],1.096)

if __name__=="__main__":unittest.main()
