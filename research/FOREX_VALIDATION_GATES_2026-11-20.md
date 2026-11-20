# Forex validation gates — 2026-11-20 (research only)

Status: **No newly verified profitable backtest. No live/demo execution authorization.**

## Confirmed implementation review

- `forex_backtest.py` currently accepts **EURUSD and GBPUSD only**; USDJPY, XAUUSD and AUDUSD are **not supported** by its USD pip-value sizing. Do not label results for those three as tested.
- Input OHLC is assumed **mid-price**; spread is applied on entry and exit. Candle ambiguity uses stop-first and gaps can worsen fills.
- Slippage is modeled at entry/exit; **commission, swap, margin, broker stop levels, dynamic currency conversion and volume limits beyond the minimum are not modeled**.
- The daily $6 realized loss and $15 realized profit controls block *new entries*, not existing trades or gap losses.
- Existing `.github/workflows/forex-tests.yml` executes Python unit tests on branch pushes/PRs. Workflow configuration is not proof of passing CI.
- Historical XAUUSD M15 v2 MT5 audit is **REJECTED**: 75 trades, 24% wins, -$57.12 net, 60.89% equity drawdown; no entries after February 2024.

## Required sequence before accepting a candidate

1. **Freeze raw inputs:** data source, immutable file checksum, symbol, UTC timestamps, bid/ask/mid provenance, timeframe, missing bars and session/calendar coverage.
2. **Broker feasibility:** verify contract size, minimum and step lot, tick size/value in USD, stops/freeze levels, margin/leverage, swap, commission and variable spread for each of EURUSD, GBPUSD, USDJPY, XAUUSD and AUDUSD. Reject any signal where minimum-lot worst-case stop loss (including fees/slippage allowance) exceeds 3% current equity.
3. **Implement symbol-specific valuation** before adding USDJPY, XAUUSD or AUDUSD to the supported backtest universe. USDJPY pip value in a USD account depends on USDJPY price; Gold uses contract/tick economics. Do not copy EURUSD's $10/pip/lot assumption.
4. **Chronological evaluation:** 60% development, 20% validation, 20% untouched holdout, preserving warmup only from preceding history and no holdout-driven tuning. Report separate results by year and by symbol; include 2025–26 coverage diagnostics.
5. **Costs:** replay variable bid/ask spreads when available; stress spread at 1.0/1.5/2.0/3.0 pips for FX only when meaningful, plus entry/exit slippage and commissions/swaps. Do not apply FX pip scenarios to Gold without converting units and broker specs.
6. **Acceptance report:** total trades, wins, win rate, net USD, net expectancy/trade, profit factor, maximum equity drawdown, worst daily realized P&L, consecutive losses, skipped signals by cause (min-lot, margin, stop distance, session, daily halt), and confidence intervals. Zero trades is **not validated**, not a 0% or 100% win rate.
7. **Out-of-sample and forward gate:** reject if profitability depends on optimistic costs, if net expectancy <=0, profit factor <=1, risk violations occur, or sample size is insufficient. Target 75% wins only as a measured aspiration; never promise $15–$20 daily returns.

## Immediate engineering priorities

- Add a **diagnostic-only signal rejection counter** to distinguish no signals from rejected entries, with unit tests.
- Add instrument-aware USD tick-value sizing and broker minimum-lot/margin/stop-level checks before enabling USDJPY, XAUUSD and AUDUSD.
- Obtain real timestamped historical data and broker contract specifications; run reproducible tests and attach full command, dataset checksum, logs and CI URL.

No production Telegram bot, live trading path or `main` modifications are authorized by this note.
