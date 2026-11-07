"""Acceptance gate must never approve exploratory candidates for live use."""
import unittest
from forex_research_acceptance_gate import assess


def metrics(trades=120, win_rate=80, pf=1.5, dd=8, pnl=12):
    return {"trades": trades, "win_rate_pct": win_rate, "profit_factor": pf,
            "max_drawdown_pct": dd, "net_pnl_usd": pnl}


class ForexResearchAcceptanceGateTests(unittest.TestCase):
    def test_strong_exploratory_result_still_not_live_approved(self):
        result = assess({"results": {"s": {"train": metrics(), "holdout": metrics()}}}, "s")
        self.assertTrue(result["research_metrics_pass"])
        self.assertFalse(result["accepted"])
        self.assertIn("independent_forward_and_broker_validation_required", result["reasons"])

    def test_negative_training_fails_even_with_profitable_holdout(self):
        result = assess({"results": {"s": {"train": metrics(pnl=-10), "holdout": metrics()}}}, "s")
        self.assertFalse(result["research_metrics_pass"])
        self.assertIn("train_nonpositive_profit", result["reasons"])

    def test_small_sample_fails(self):
        result = assess({"results": {"s": {"train": metrics(trades=31), "holdout": metrics(trades=26)}}}, "s")
        self.assertIn("holdout_insufficient_trades", result["reasons"])

    def test_invalid_ranges_and_boolean_metrics_fail_closed(self):
        for bad in (
            metrics(trades=True),
            metrics(win_rate=101),
            metrics(win_rate=-1),
            metrics(pf=-0.5),
            metrics(dd=101),
            metrics(trades=120.5),
        ):
            result = assess({"results": {"s": {"train": bad, "holdout": metrics()}}}, "s")
            self.assertFalse(result["research_metrics_pass"])
            self.assertTrue(any(reason.startswith("train_") for reason in result["reasons"]))

    def test_missing_and_nan_fail_closed(self):
        self.assertFalse(assess({"results": {}}, "s")["accepted"])
        result = assess({"results": {"s": {"train": metrics(pf=float("nan")), "holdout": metrics()}}}, "s")
        self.assertIn("train_profit_factor_missing_or_invalid", result["reasons"])


if __name__ == "__main__":
    unittest.main()
