import unittest
from ai_review import AGENT_ROLES, run_review, snapshot_fingerprint, validate_snapshot


def sample_snapshot():
    return {
        "instrument": "EURUSD",
        "timeframe": "M15",
        "decision_timestamp": "2026-11-28T12:00:00Z",
        "market_data_timestamp": "2026-11-28T11:45:00Z",
        "candidate": {"side": "BUY", "score": 78, "entry": 1.1, "stop": 1.09, "target": 1.12},
        "risk_context": {"gate_pass": True, "daily_pnl": 0.0},
        "news_context": {"status": "UNKNOWN", "events": []},
    }


def agent_for(role, assessment="neutral"):
    def fake(snapshot, sid):
        return {
            "agent": role, "snapshot_id": sid, "assessment": assessment,
            "evidence": [], "risks": [], "invalidation": "candidate invalidated",
            "missing_data": [], "recommendation": "advisory only",
        }
    return fake


class MultiAgentReviewTests(unittest.TestCase):
    def test_snapshot_fingerprint_stable(self):
        s = sample_snapshot()
        self.assertEqual(snapshot_fingerprint(s), snapshot_fingerprint(dict(s)))

    def test_future_market_data_rejected(self):
        s = sample_snapshot()
        s["market_data_timestamp"] = "2026-11-28T12:01:00Z"
        self.assertIn("market data timestamp is after decision timestamp",
                      validate_snapshot(s, now="2026-11-28T12:05:00Z"))

    def test_future_decision_time_rejected(self):
        s = sample_snapshot()
        self.assertIn("decision timestamp is in the future",
                      validate_snapshot(s, now="2026-11-28T11:00:00Z"))

    def test_missing_snapshot_field_abstains(self):
        s = sample_snapshot()
        del s["news_context"]
        result = run_review(s, {}, hard_gates_pass=True, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.status, "ABSTAIN")
        self.assertEqual(result.verdict, "WAIT")

    def test_agent_output_snapshot_mismatch_abstains(self):
        agents = {r: agent_for(r) for r in AGENT_ROLES}
        original = agents["strategy"]
        def bad(snapshot, sid):
            out = dict(original(snapshot, sid))
            out["snapshot_id"] = "wrong"
            return out
        agents["strategy"] = bad
        result = run_review(sample_snapshot(), agents, True, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.status, "ABSTAIN")
        self.assertIn("strategy: snapshot ID mismatch", result.validation_errors)

    def test_hard_risk_gate_failure_forces_wait(self):
        agents = {r: agent_for(r, "bullish") for r in AGENT_ROLES}
        result = run_review(sample_snapshot(), agents, False, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.verdict, "WAIT")
        self.assertTrue(result.hard_gate_blocked)

    def test_agent_exception_abstains(self):
        agents = {r: agent_for(r) for r in AGENT_ROLES}
        def fail(snapshot, sid):
            raise TimeoutError("offline mock timeout")
        agents["news"] = fail
        result = run_review(sample_snapshot(), agents, True, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.status, "ABSTAIN")
        self.assertTrue(any("news: agent failed" in e for e in result.validation_errors))

    def test_conflicting_views_preserve_dissent_and_wait(self):
        agents = {r: agent_for(r, "neutral") for r in AGENT_ROLES}
        agents["bull_case"] = agent_for("bull_case", "bullish")
        agents["bear_case"] = agent_for("bear_case", "bearish")
        result = run_review(sample_snapshot(), agents, True, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.status, "COMPLETE")
        self.assertEqual(result.verdict, "WAIT")
        self.assertTrue(result.dissent)

    def test_consensus_labels_are_candidate_only(self):
        agents = {r: agent_for(r, "bullish") for r in AGENT_ROLES}
        result = run_review(sample_snapshot(), agents, True, now="2026-11-28T13:00:00Z")
        self.assertEqual(result.verdict, "BUY_CANDIDATE")
        self.assertEqual(len(result.agent_outputs), len(AGENT_ROLES))


if __name__ == "__main__":
    unittest.main()
