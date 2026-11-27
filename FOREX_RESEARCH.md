# Forex research workflow (XM Standard, USD $100 baseline)

Status: **Research code and the historical smoke workflow exist. A historical run on 2026-11-10 completed successfully, but its one-day artifacts have expired; exploratory findings are summarized below. No strategy is validated.**

## Public data (while away from MT5 desktop)
Download EURUSD 5-minute OHLC CSV from a historical provider such as
https://www.dukascopy-node.app/instrument/eurusd
and verify its timestamp timezone and whether prices are mid, bid or ask.
Do not assume that a third-party spread matches XM Standard.

## Historical data workflow
The GitHub Actions research workflow fetches Yahoo Finance 1-hour candles using a default 2y period for EURUSD, GBPUSD, AUDUSD, USDJPY and GOLD. The downloader also supports 6mo and 1y; --count applies only to crypto. Hourly candles are not broker bid/ask ticks. The generic shared replay is skipped for USDJPY because account-currency conversion must be dynamic; USDJPY is handled by the dedicated XM Standard Forex model in this workflow.

```bash
pip install -r requirements.txt
python forex_data_prepare.py downloaded.csv eurusd_m5_utc.csv --timezone UTC
python forex_backtest.py eurusd_m5_utc.csv --symbol EURUSD --spread-pips 1.5
python -m unittest discover -p 'test_forex*.py'
```

If the data is bid-only or ask-only, do **not** treat it as mid-price:
convert using contemporaneous bid/ask quotes or adapt the execution model.
The fixed 1.5-pip spread is a **scenario assumption**, not an XM quote.
Run sensitivity cases at 1.0, 1.5, 2.0 and 3.0 pips, and slippage stress.
Never optimize parameters on the final out-of-sample period.

## Validation gates before demo signals
1. Confirm data source, timestamp zone, candle type, coverage and gaps.
2. Run unit tests; inspect every failure before using results.
3. Split chronologically: 60% train, 20% validation, 20% untouched test.
4. Report sample size, net expectancy, profit factor, win rate, drawdown,
   losing streaks, and proportion of signals skipped due to minimum lot.
5. Check broker contract specifications, margin, minimum stop distance,
   actual spread and commission/swap for each symbol.
6. Demo forward test before any live trading.

The current backtester does not model broker margin, commissions or swaps.
A $100 account with 3% risk and 0.01 minimum lot may still have zero valid
trades; **never force a minimum lot above the risk budget**.
A 75% win rate is a research goal, not a performance claim.

## Updated research targets (2026-11-04)
- Starting equity: USD 100.
- Per-trade planned risk: **3% of current equity maximum** (aggressive).
- Baseline target: **2R**. Three $3-risk wins imply about $18 gross at fixed initial equity, before costs.
- Daily profit objective: **$15-$20, aspirational only**, not a guaranteed income or trade quota.
- Backtester now checks **$6 realized UTC daily loss** and **$15 realized UTC daily profit** before new entries; this is not a hard loss cap.
- Actual fill losses can exceed planned risk due to gaps/slippage.
- Do not force trades when broker minimum lot exceeds risk budget.
- The backtester now uses `DailyRiskGuard` to gate new entries, but overnight positions, unrealized losses, and gaps can exceed thresholds. Integration is committed; CI tests and historical backtests still need verification.
- The separate XM Standard comparison includes 0.5%, 1%, 2% and 3% risk scenarios; these are research settings, not a live recommendation.

## Verified prior smoke-run findings (2026-11-10)
The six-job historical workflow completed successfully, but the artifacts were retained for only one day and are now unavailable. The generic signal replay at its default 0.5% risk and 0.01 minimum quantity produced zero completed trades on all four tested Forex/gold symbols: EURUSD (4,202 candles/327 signals), GBPUSD (4,266/345), USDJPY (4,181/254), and GOLD (3,415/348). Their win rates were null (no trades), not 0%.

The separate XM Standard exploratory comparison did produce EURUSD pullback trades at 2% risk and 1.5R: train 87 trades, 43.68% wins, +$12.79; holdout 39 trades, 51.28% wins, +$16.89, profit factor 1.473. This is not independent validation: multiple entry/risk/RR variants were compared, and commission, slippage, swaps, daily-loss guard and broker fills were not modeled. The 75% target remains unverified.

## CI test status
A GitHub Actions workflow at `.github/workflows/forex-tests.yml` is configured to run the offline Python tests on future pushes and pull requests. Confirmed successful runs on 2026-11-26: Forex research tests #91 (68 tests), Forex research unit tests #79 (68 tests), and ProSignals Development Tests #206 (78 tests). These are code/unit checks, not evidence of profitability.
