# ProSignals development: shared backtesting and risk foundation

This branch adds **experimental, paper-only** modules for Forex (including gold)
and crypto. It DOES NOT alter either original signal script, their schedules, or
live Telegram alerts. Neither original script currently executes trades.

## Modules

- `shared_risk.py` provides risk-budgeted position sizing, minimum order sizes,
  maximum gross notional and a daily realized-loss gate.
- `shared_backtest.py` provides a single-position, long/short OHLC simulator
  with next-candle-open fills and conservative stop-first handling if both
  exits lie inside the same candle.
- `tests/test_shared.py` includes introductory unit tests.

Run tests: `python -m unittest discover -s tests -v`.

## Not yet implemented — do not use for real money

- Historical data ingestion, reconciliation, spread and accurate per-venue fees
- Validated instrument contract sizes, pip/tick values, quote-to-account FX
  conversion, margin requirements, leverage, swaps and exchange precision
- Exact original signal logic replay; signals must be built using only bars
  available **before** each trade, with no forward-looking information
- Partial profits (TP1/TP2), break-even adjustments, portfolio correlations
  and multiple simultaneous positions
- Intrabar/tick event resolution, exchange/broker-specific order handling
- Walk-forward and out-of-sample evaluation, drawdown and profit statistics
- MT5, TradingView, Bitget connections, chatbot and any execution permissions

The 0.5% risk-per-trade setting is only an initial simulation default.
The 80% win-rate goal remains unverified, and should not be interpreted as
a probability or promise. The production branch has not been modified.
