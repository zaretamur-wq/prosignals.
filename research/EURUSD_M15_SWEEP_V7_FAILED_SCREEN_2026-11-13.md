# ProSignals EURUSD M15 Sweep v7 — research only (2026-11-13)

**FAILED historical screening; not a profitable bot.** Standalone MQL5 demo candidate provided separately; no live deployment.

Original liquidity-sweep/rejection strategy informed by public Nexus project concepts; no third-party code copied. Signal is completed M15 candle sweeping 24 prior bars by >0.03 ATR, closing back inside with directional rejection body, countertrend versus M15 EMA200. Entry next bar, 2xATR stop, 2R target, 16-bar timeout; sampled spread and 0.2 pip adverse slippage each side. Session hours 12–20 in exported broker time, actual broker UTC offset not verified.

| Period | Trades | Win% | PF | Net R | Drawdown R | TP | Stop | Timeout |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022–2024 development | 420 | 42.86 | 0.946 | -10.49 | -27.71 | 52 | 160 | 208 |
| 2025–2026 holdout | 370 | 44.05 | 0.910 | -14.70 | -30.36 | 35 | 136 | 199 |

Best development candidate among 96 variants with >=80 trades was still unprofitable, as was holdout. The complete script and CSV results are supplied as standalone files. Theoretical OHLC fills are not MT5 real-tick fills.

Standalone demo MQL5 file ProSignals_EURUSD_M15_Sweep_Demo_v7.mq5: requires EURUSD 5-digit M15 demo account, default orders OFF, maximum 1% risk, rejects lots below broker minimum or too much margin, 3 trades/day, two-loss halt, $6 daily PnL stop and 16-bar time exit. Source has not been compiled in MetaEditor here. Broker time zone must be verified. $100 minimum-lot constraints could correctly prevent all trades. No main, live execution or Telegram modifications.

Decision: Do not claim profitability or promote to live. Forward demo experimentation is permitted with explicit awareness that historical tests lost money; seek genuinely positive signal-only and randomized-baseline outcomes before promotion.