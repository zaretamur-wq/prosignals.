import unittest
from research_session_consistency import screen_session


def metrics(trades=40, pnl=5, pf=1.2, dd=7, wr=60):
    return {"trades": trades, "win_rate_pct": wr, "net_pnl_usd": pnl, "profit_factor": pf, "max_drawdown_pct": dd}


class SessionConsistencyTests(unittest.TestCase):
    def test_rejects_london_second_half_loss(self):
        c = {"results": {"london_holdout_first_1.0R": {"holdout": metrics()},
                         "london_holdout_second_1.0R": {"holdout": metrics(40, -20, .5, 27)}}}
        result = screen_session(c, "london")
        self.assertFalse(result["consistent_across_halves"])
        self.assertIn("second_unprofitable", result["reasons"])
        self.assertIn("second_drawdown", result["reasons"])

    def test_rejects_small_samples(self):
        c = {"results": {f"ny_holdout_{half}_1.0R": {"holdout": metrics(15)}
                         for half in ("first", "second")}}
        self.assertFalse(screen_session(c, "ny")["consistent_across_halves"])

    def test_consistent_diagnostic_not_approval(self):
        c = {"results": {f"london_holdout_{half}_2.0R": {"holdout": metrics()}
                         for half in ("first", "second")}}
        result = screen_session(c, "london", 2.0)
        self.assertTrue(result["consistent_across_halves"])
        self.assertIn("NOT independent validation", result["note"])

    def test_rejects_impossible_statistics(self):
        for changed in ({"wr": 105}, {"wr": -1}, {"pf": -0.1},
                        {"dd": 101}, {"dd": -1}, {"trades": -2}):
            m = metrics(**changed)
            c = {"results": {f"ny_holdout_{half}_1.0R": {"holdout": m}
                             for half in ("first", "second")}}
            result = screen_session(c, "ny")
            self.assertFalse(result["consistent_across_halves"])
            self.assertIn("first_invalid_range", result["reasons"])

    def test_rejects_missing_win_rate_and_bool_threshold(self):
        m = metrics()
        del m["win_rate_pct"]
        c = {"results": {"ny_holdout_first_1.0R": {"holdout": m}}}
        self.assertIn("first_invalid", screen_session(c, "ny")["reasons"])
        with self.assertRaises(ValueError):
            screen_session(c, "ny", min_trades_per_half=True)

    def test_rejects_missing_or_invalid(self):
        self.assertIn("first_missing", screen_session({"results": {}}, "ny")["reasons"])
        c = {"results": {"ny_holdout_first_1.0R": {"holdout": metrics(pnl=float("nan"))}}}
        self.assertIn("first_invalid", screen_session(c, "ny")["reasons"])


if __name__ == "__main__":
    unittest.main()
