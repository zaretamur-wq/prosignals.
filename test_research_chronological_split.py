"""Offline tests for chronological data partitions."""
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from research_chronological_split import chronological_splits, split_csv

class ChronologicalSplitTests(unittest.TestCase):
    def test_sizes_and_order(self):
        a,b,c=chronological_splits(list(range(100)))
        self.assertEqual((len(a),len(b),len(c)),(60,20,20))
        self.assertEqual((a[-1],b[0],b[-1],c[0]),(59,60,79,80))

    def test_embargo(self):
        a,b,c=chronological_splits(list(range(100)),embargo=3)
        self.assertEqual((a[-1],b[0],b[-1],c[0]),(59,63,79,83))

    def test_reject_bad_inputs(self):
        for n in ([],list(range(2))):
            with self.assertRaises(ValueError):
                chronological_splits(n)
        with self.assertRaises(ValueError):
            chronological_splits(list(range(100)),embargo=-1)

    def test_csv_rejects_unsorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"data.csv"
            pd.DataFrame({"time":["2026-01-02","2026-01-01"],"close":[1,2]}).to_csv(p,index=False)
            with self.assertRaises(ValueError):
                split_csv(p,Path(tmp)/"output")

    def test_csv_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"data.csv"
            pd.DataFrame({"time":pd.date_range("2026-01-01",periods=100,freq="h",tz="UTC"),
                          "close":range(100)}).to_csv(p,index=False)
            result=split_csv(p,Path(tmp)/"output",embargo=2)
            self.assertEqual((result["train_rows"],result["validation_rows"],result["test_rows"]),(60,18,18))
            self.assertTrue((Path(tmp)/"output"/"split_manifest.json").exists())

if __name__=="__main__":
    unittest.main()
