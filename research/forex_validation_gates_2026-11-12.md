# Forex-first research acceptance gates (2026-11-12)

Research-only specification; not an approved trading strategy or live-execution configuration.

## Universe and assumptions
- Primary: EURUSD, GBPUSD, USDJPY, XAUUSD, AUDUSD. Crypto secondary.
- Initial equity USD 100; proposed risk ceiling 3% of current equity per position, including open correlated positions.
- Baseline reward:risk 2:1, with actual fills and costs deducted.
- Daily realized-loss entry halt at USD 6, including commissions and slippage; unrealized exposure and gaps can exceed this limit.
- USD 15-20/day is an aspiration, not a projected return. No minimum trade count or daily-profit guarantee.

## Chronological validation
1. Freeze candidate rules and parameters using training data only.
2. Reserve later, strictly chronological out-of-sample periods and report them separately. Do not retune on held-out periods.
3. For each symbol, document broker, quote timezone, spread distribution, commission, swaps, slippage, contract size, tick value, lot step, minimum lot, and stop-distance restrictions.
4. Reject any trade whose risk cannot fit the available equity after rounding volume to the broker's allowed lot step; never round upward past the risk ceiling.
5. Include bid/ask-aware entries and exits, intrabar stop/target ambiguity handled conservatively, no lookahead, and no overlapping signals that breach aggregate risk.
6. Calculate sample size, win rate and uncertainty interval, net profit, expectancy, profit factor, maximum equity drawdown, losing streak, and daily-loss-halt breaches; report by pair and combined.
7. Test spread/slippage stress scenarios, alternate chronological windows and parameter stability. Preserve raw reports and reproducible command/configuration.
8. A 75% win rate is **unverified** unless the held-out results demonstrate it after all costs and broker constraints. At 1:2 R:R, win rate alone is insufficient evidence of robustness.

## Safety and scope
No changes to main, live trading, order placement, production Telegram bot, credentials, or deployment. Do not present synthetic results as observed performance. Never claim that the USD 6 halt guarantees a USD 6 maximum daily loss.

## Current verification status
This document records acceptance criteria only. No new strategy backtest, broker execution test, or validated 75% result was produced by this document.
