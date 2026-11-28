# ProSignals Multi-Agent Trade Review — Research Design

Status: Research proposal; no live trading or production signal changes.
Target branch: `development/shared-backtesting-risk`
Purpose: Evaluate whether a structured multi-agent review layer improves signal quality, risk-adjusted outcomes, and decision discipline compared with the current deterministic signal engine.

## Design principle
Agents provide independent analysis and challenge, not votes that manufacture confidence. The existing deterministic engine remains the source of candidate setups and hard risk rules. AI review must never override deterministic risk gates, invent market data, or place orders.

## Proposed roles
1. **Market/Setup Scanner (existing engine first):** produces candidate side, score, entry, stop, target, timeframe, indicator/structure reasons, and timestamp. Do not duplicate scanner logic with an LLM.
2. **News & Event Analyst:** checks supplied/verified news and economic calendar context; reports source timestamps, affected instruments, event risk, and uncertainty. If no verified news feed is available, state `UNKNOWN`, never `CLEAR`.
3. **Strategy Analyst:** independently assess trend, structure, session context, momentum, pullback/breakout quality, and setup consistency against the strategy rules; cite only input fields.
4. **Bull Case:** strongest evidence supporting the candidate and what must hold.
5. **Bear Case / Skeptic:** strongest opposing case, invalidation, traps (e.g., liquidity sweep vs. genuine breakout), and missing confirmation.
6. **Risk Analyst:** independently recompute entry/stop distance, risk/reward, size, exposure, correlated positions, daily loss status, and execution constraints from structured inputs. Deterministic risk functions remain authoritative.
7. **Desk Lead / Synthesizer:** summarize evidence and disagreements; output `BUY_CANDIDATE`, `SELL_CANDIDATE`, or `WAIT`. Candidate labels are informational only and do not trigger execution. Show reasons, unresolved conflicts, invalidation, and data-quality status.

## Structured review contract
Every review consumes a frozen snapshot containing: instrument, timeframe, decision timestamp, candle data timestamp, candidate signal, entry/stop/target, indicator values, market-structure features, session, verified news/event records (or explicit unavailable state), spread/slippage/commission assumptions, account equity, existing exposure, and risk-policy state.

Each agent returns machine-parseable JSON:
- `agent`, `snapshot_id`, `timestamp`
- `assessment` (bullish/bearish/neutral/unknown)
- `evidence[]` (input field/value + short rationale)
- `risks[]`, `invalidation`, `missing_data[]`
- `confidence` (calibrated only after validation; otherwise qualitative/uncalibrated)
- `recommendation` and `recommendation_conditions[]`

The synthesizer must preserve dissent and mark conflicting or unsupported claims. No numerical confidence is displayed as a probability until calibration has been measured.

## Hard gates (non-negotiable)
- No look-ahead: all inputs must be available at the decision timestamp; signals occur after candle close and simulated execution uses the next bar/open per existing backtest convention.
- No agent can bypass daily loss halt, max-risk, sizing, spread, margin, minimum-lot, news-block, or instrument validation gates.
- Missing/stale/contradictory data yields `WAIT` or `REVIEW_UNAVAILABLE`; unknown news status is not treated as clear.
- Same-bar stop/target ambiguity follows conservative existing backtest assumptions.
- Agents do not place, modify, or close live orders. Research/demo only.
- Store provider/model/version, prompt version, snapshot ID, and raw structured outputs for audit; avoid secrets in logs.

## Evaluation plan
Run a chronological, leakage-safe comparison on the same candidate trades and frozen inputs:
A. Existing deterministic baseline.
B. Baseline plus agent review (first as advisory; then test a predeclared filter only if justified).

Report trade count, win rate, net expectancy after realistic spread/slippage/commission, profit factor, max drawdown, risk-adjusted metrics, missed winners, avoided losers, false blocks, latency, cost, and breakdowns by symbol/session/regime. Use chronological train/calibration/holdout splits and keep holdout untouched until criteria are set. Evaluate both agent abstention and disagreement. No cherry-picking or optimizing prompts on holdout results.

## Implementation phases
1. **Offline schema and mock-agent harness:** validate JSON contract, snapshot immutability, deterministic reproducibility, failure/timeout handling, and disagreement preservation; no LLM API required initially.
2. **Advisory-only integration prototype:** analyze a small set of existing candidate events; never change alerts or trade eligibility.
3. **Historical replay evaluation:** compare baseline vs. agent advisory/filter variants using identical candidate snapshots and cost assumptions; include failure cases and agent outages.
4. **Paper/demo shadow mode:** produce side-by-side reviews and log outcomes without execution or changing production alerts.
5. **Promotion gate:** require repeatable, cost-inclusive, out-of-sample improvement and operational tests before considering any influence on signal filtering. Keep live/production isolated.

## Initial acceptance criteria for the prototype
- Valid schema for all agent outputs; invalid outputs safely rejected.
- Snapshot/time validation prevents future data from being included.
- Deterministic risk gate remains unchanged and cannot be overridden.
- Agent failure, stale data, or missing news yields explicit abstention.
- Baseline signal and all dissenting agent views are retained in logs.
- Backtest comparison can measure added value without changing the baseline.

## Next technical task
Implement the offline schema and mock-agent harness as a separate research module with unit tests. Keep dependencies minimal and avoid introducing paid APIs until the harness and evaluation protocol are ready.
