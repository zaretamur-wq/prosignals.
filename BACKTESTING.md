# Historical backtesting: research-only preview

This branch includes a replay tool for **both** existing strategies:
- Forex and gold: `signals.py` (1-hour entry + completed 4-hour trend)
- Crypto: `crypto_signals.py` (5-minute entry + 15-minute/1-hour trends)

Existing Telegram scripts on `main` are not changed. The new CI workflow tests
source compilation and five unit cases; it does not run full historical backtests.

## Input data requirements

Historical candle files must be CSV, with strictly increasing UTC timestamps
and columns `time,open,high,low,close`. Crypto also requires `vol`. Include
fully closed 1-hour Forex or 5-minute crypto candles with uninterrupted time
intervals, adjusted for expected market closures.

Forex replay needs at least 852 hourly candles; crypto replay needs at least
2602 five-minute candles. More years and different regimes are necessary to
draw meaningful conclusions. The script runs offline and DOES NOT fetch historical
data automatically.

## Run example (illustrative only; NOT broker settings)

```bash
python historical_replay.py --market crypto --symbol BTC --csv data/BTC_5m.csv \
  --capital 100 --quantity-step 0.000001 --min-quantity 0.000001 \
  --price-value 1 --commission-per-unit-side 0 --slippage 0.0005
```

For Forex/gold, **do not reuse the crypto specification**. Obtain broker-verified
lot step, min lot, contract multiplier, currency conversion, allowed leverage,
spread and minimum margin before meaningful cash-based outcomes. These
values differ by instrument and account currency.

## Critical methodological limitations

- This is **not** a faithful end-to-end performance test yet: historical
  derivatives/order books/funding, point-in-time economic calendar/news, the
  crypto BTC cross-asset trend filter, cooldowns and frequency limits are
  not reproduced.
- Original crypto TP1 then move-to-breakeven and TP2 is simplified to TP2;
  the execution simulator handles only one open trade at a time.
- Both assets use simplified next-bar fills and stop-first OHLC ambiguity.
  Broker spread, swap, borrowing, tick liquidity and market impact are not
  modeled. Incorrect parameters can make P&L completely misleading.
- Original signal scores are heuristic, **not** win probabilities.
- The tool is research-only and has no exchange or broker-order integration.
- Any future claims require time-separated out-of-sample testing and
  extensive forward paper trading, with fee-aware results and sufficient
  samples. A goal of 80% wins is **not verified**.

## Tests
`python -m unittest discover -s tests -v`

## Development roadmap
1. Historical data collection with timestamp and missing-bar validation.
2. Exact per-market replay: news, derivatives, cooldowns, BTC correlation,
   partial targets and simultaneous portfolio risk.
3. Fees, spread, margin and point-in-time quote conversion.
4. Train/validation/test splits, walk-forward, trade ledger and drawdown.
5. Forward paper trading; only then consider chatbot-driven execution.
