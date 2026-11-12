# EURUSD M15 OHLC exploratory screen — 2026-11-13

**Research only. No profitable EA established. Do not deploy to a demo chart or live broker as an automated execution strategy.**

## Input and method

User-supplied EURUSD M15 100,001 records, November 2022–November 2026, including sampled spread. Chronological development segment 2022–2024; holdout 2025–2026. Signals on completed M15 candles, next-bar open entry, bid OHLC, spread for buys/sell exits, 0.2 pip extra adverse slippage per side, 12-bar time exit and pessimistic stop-first interpretation if both stop and TP touched. This is an approximate research simulator, **not** MT5 real tick execution, and it omits broker-specific lot constraints, commission, swaps, and margin. Results are in R, **not dollars**.

## Fixed baseline, 1.5 ATR stop / 2R target

12 entry rules tested: H1-trend EMA20 and EMA50 reclaims, 20 and 40 bar breakouts, volatility-filtered breakouts, RSI trend reclaim, trend momentum, z-score mean reversion, H1-filtered z-score mean reversion, RSI extreme mean reversion, and EMA20 continuation. All had **holdout PF below 1.0**, and negative net R. The highest holdout PF in this group was 0.981 for H1-filtered z-score (462 trades, 42.6% wins, -4.51R); unfiltered z-score PF 0.979 (411 trades, 41.8% wins, -4.81R). These are not profitable.

## Additional development-only exit screen

Screened reward-to-risk targets 0.75, 1.0, 1.25, 1.5 and 2.0, with ATR stop multiples 1.0, 1.5 and 2.0 across 12 entry rules (180 combinations) on development period only. Highest development PF: unfiltered z-score mean reversion, 1.5R target / 2 ATR stop; 430 development trades, win rate 45.6%, PF 1.039, +7.55R. Independently evaluated on the holdout: 365 trades, win rate 46.0%, PF 0.930, -11.79R, max peak-to-trough trade-sum drawdown 31.90R. **Rejected.** Other top development candidates also failed holdout.

## Decision / blockers

- No candidate showed convincing profitable holdout performance. No v7 EA or production changes are justified from these tests.
- The aspirational 75% win rate is not verified and was not approached by these candidates.
- Next: check data timestamp/session alignment and simulate risk limits and broker minimum lot/margin; then explore materially different regime/event/session structures using new training data, with a fresh untouched holdout if iterating after inspecting this one.
- Neither `main` nor live execution nor the production Telegram bot is changed.
