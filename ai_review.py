"""Offline, advisory-only multi-agent review harness for ProSignals research.

This module is intentionally dependency-light and does not connect to trading APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Callable, Mapping

ASSESSMENTS = {"bullish", "bearish", "neutral", "unknown"}
AGENT_ROLES = ("strategy", "news", "risk", "skeptic")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO-8601 text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def snapshot_fingerprint(snapshot: Mapping[str, Any]) -> str:
    """Stable fingerprint for a decision snapshot, excluding any supplied ID."""
    payload = {k: v for k, v in snapshot.items() if k != "snapshot_id"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def validate_snapshot(snapshot: Mapping[str, Any], now: str | None = None) -> list[str]:
    errors: list[str] = []
    required = ("instrument", "timeframe", "decision_timestamp", "market_data_timestamp",
                "candidate", "risk_context", "news_context")
    for key in required:
        if key not in snapshot:
            errors.append(f"missing field: {key}")
    if errors:
        return errors
    try:
        decision = _parse_time(snapshot["decision_timestamp"])
        market_time = _parse_time(snapshot["market_data_timestamp"])
        current = _parse_time(now) if now else datetime.now(timezone.utc)
        if market_time > decision:
            errors.append("market data timestamp is after decision timestamp")
        if decision > current:
            errors.append("decision timestamp is in the future")
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
    if not isinstance(snapshot["candidate"], Mapping):
        errors.append("candidate must be an object")
    if not isinstance(snapshot["risk_context"], Mapping):
        errors.append("risk_context must be an object")
    if not isinstance(snapshot["news_context"], Mapping):
        errors.append("news_context must be an object; unavailable news must be explicit")
    return errors


def validate_agent_output(output: Mapping[str, Any], expected_role: str,
                         snapshot_id: str) -> list[str]:
    errors: list[str] = []
    required = ("agent", "snapshot_id", "assessment", "evidence", "risks",
                "invalidation", "missing_data", "confidence", "recommendation",
                "recommendation_conditions")
    for key in required:
        if key not in output:
            errors.append(f"missing output field: {key}")
    if errors:
        return errors
    if output["agent"] != expected_role:
        errors.append("agent role mismatch")
    if output["snapshot_id"] != snapshot_id:
        errors.append("snapshot ID mismatch")
    if output["assessment"] not in ASSESSMENTS:
        errors.append("invalid assessment")
    for field in ("evidence", "risks", "missing_data", "recommendation_conditions"):
        if not isinstance(output[field], list):
            errors.append(f"{field} must be a list")
    if not isinstance(output["recommendation"], str):
        errors.append("recommendation must be text")
    if not isinstance(output["confidence"], str):
        errors.append("confidence must be qualitative text until calibrated")
    return errors


@dataclass(frozen=True)
class ReviewResult:
    snapshot_id: str
    status: str
    verdict: str
    agent_outputs: dict[str, dict[str, Any]]
    dissent: tuple[str, ...]
    hard_gate_blocked: bool
    validation_errors: tuple[str, ...]


Agent = Callable[[Mapping[str, Any], str], Mapping[str, Any]]


def run_review(snapshot: Mapping[str, Any], agents: Mapping[str, Agent],
              hard_gates_pass: bool, now: str | None = None) -> ReviewResult:
    """Run injected offline/mock agents and fail closed on invalid inputs or outputs."""
    sid = snapshot_fingerprint(snapshot)
    snapshot_errors = validate_snapshot(snapshot, now=now)
    if snapshot_errors:
        return ReviewResult(sid, "ABSTAIN", "WAIT", {}, tuple(), not hard_gates_pass,
                           tuple(snapshot_errors))
    outputs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    dissent: list[str] = []
    for role in AGENT_ROLES:
        agent = agents.get(role)
        if agent is None:
            errors.append(f"{role}: agent not configured")
            continue
        try:
            raw = dict(agent(snapshot, sid))
            problems = validate_agent_output(raw, role, sid)
            if problems:
                errors.extend(f"{role}: {problem}" for problem in problems)
                continue
            outputs[role] = raw
        except Exception as exc:
            errors.append(f"{role}: agent failed ({type(exc).__name__})")
    if errors or not hard_gates_pass or len(outputs) != len(AGENT_ROLES):
        return ReviewResult(sid, "ABSTAIN", "WAIT", outputs, tuple(dissent),
                           not hard_gates_pass, tuple(errors))
    strategy = outputs["strategy"]["assessment"]
    risk = outputs["risk"]["assessment"]
    skeptic = outputs["skeptic"]["assessment"]
    news_status = str(snapshot["news_context"].get("status", "UNKNOWN")).upper()
    if news_status not in {"VERIFIED", "CLEAR", "CHECKED"}:
        dissent.append("news/event context is unknown or unverified")
        verdict = "WAIT"
    elif strategy == "bullish" and skeptic == "bearish":
        dissent.append("strategy and skeptic conflict: bullish thesis challenged")
        verdict = "WAIT"
    elif strategy == "bearish" and skeptic == "bullish":
        dissent.append("strategy and skeptic conflict: bearish thesis challenged")
        verdict = "WAIT"
    elif strategy == "bullish" and risk in {"neutral", "bullish"} and skeptic != "bearish":
        verdict = "BUY_CANDIDATE"
    elif strategy == "bearish" and risk in {"neutral", "bearish"} and skeptic != "bullish":
        verdict = "SELL_CANDIDATE"
    else:
        verdict = "WAIT"
    return ReviewResult(sid, "COMPLETE", verdict, outputs, tuple(dissent),
                      False, tuple())
