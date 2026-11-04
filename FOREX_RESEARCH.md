# Forex research workflow (XM Standard, USD $100 baseline)

Status: **data ingestion and backtest code exist; no historical backtest has been run or verified.**

## Public data (while away from MT5 desktop)
Download EURUSD 5-minute OHLC CSV from a historical provider such as
https://www.dukascopy-node.app/instrument/eurusd
and verify its timestamp timezone and whether prices are mid, bid or ask.
Do not assume that a third-party spread matches XM Standard.

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
A $100 account with 0.5% risk and 0.01 minimum lot may have zero valid
trades; **never force a minimum lot above the risk budget**.
A 75% win rate is a research goal, not a performance claim.
