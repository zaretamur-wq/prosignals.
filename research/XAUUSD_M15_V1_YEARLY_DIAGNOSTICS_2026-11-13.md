# XAUUSD M15 v1 MT5 report audit — 2026-11-13

Research-only report of uploaded `ReportTester-xA.xlsx` (4TLtd-Live terminal, **Strategy Tester** with 100% real-tick historical quality). No claim of forward-test profitability.

- Total closed trades: 486; wins: 254 (52.26%); net -$72.98; PF 0.92776; max equity drawdown 89.23%.
- **Entries by year**, counted from `Orders` section and own `PS XAU Research` entry comments: 2022 **325**, 2023 **153**, 2024 **8**, 2025 **0**, 2026 **0**.
- Exit orders classified by comments: 237 TP; 194 SL; other closure types remain to be classified separately. These counts are not synonymous with winners/losers.
- The tester date range ends in 2026 but there were no eligible 2025–2026 entries. Thus the reported 52.26% is **not** a modern-market validation.
- A likely explanation is broker minimum 0.01 lots and $5 risk cap against increasing Gold ATR, but the report alone does **not** establish the cause.
- A separate instrumented EA `ProSignals_XAUUSD_M15_Research_Diagnostic_v1D.mq5` was created locally to count yearly bars, generated setups, small-lot skips, spread skips, stop restrictions, margin/risk rejects, daily stops, order rejects, session skips and accepted orders. **No strategy logic or target/stop parameters intentionally changed**, and default execution remains OFF. It has not been compiled in MetaEditor, so compilation is unverified. Treat logs as evidence only after the tester finishes and logs are saved.

Next: run diagnostic backtest on $100 demo Strategy Tester, using same settings as v1, and inspect yearly PS_GOLD_DIAG counters. Do not promote to live or claim a profit improvement before confirming modern trade eligibility and independent holdout profitability. Keep `main`, production Telegram, and live execution untouched.
