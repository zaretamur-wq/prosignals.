# MT5 measured baseline — existing user-supplied reports

Source: prior audit of ReportTester-60025526.xlsx, expert ProSignals_GBPUSD_StrictExecution_v5.
This is measured **historical MT5 tester output**, not a forward demo result.

- GBPUSD closed trades: 155 (155 entry and 155 exit deals)
- Wins: 54; win rate: 34.84%
- Net result: +12.97 **tester report units** (tester UI indicated profit in pips; do not label as verified USD)
- Profit factor: 1.08
- Closed-balance maximum drawdown: 29.31% (not intratrade equity drawdown)
- Hypothetical extra cost of 0.25 units/trade: -25.78 units, PF 0.863
- Hypothetical extra cost of 0.50 units/trade: -64.53 units, PF 0.698
- Year-by-year report units: 2022 +0.19 (3 trades); 2023 -6.31 (27); 2024 -5.77 (58); 2025 +33.30 (27); 2026 -8.44 (40).

**Decision:** Do not treat V5 as a profitable validated scalping system; do not auto-enable live orders.

Independent H1 historical screening (not identical to MT5 fills), 70/30 chronological split:
- EURUSD strict-quality holdout: -$13.81, 98 trades
- GBPUSD strict-quality holdout: +$10.50, 44 trades; development period -$3.49
- USDJPY strict-quality holdout: -$11.23, 98 trades
- XAUUSD: zero eligible trades

Next comparison: chart-pattern module vs original methods on **the same untouched M5 candles** with realistic spread/slippage, explicit broker sizing and true holdout. No assertion of improvement without a successful run and recorded output.

Provenance: user's previously supplied MT5 exports and generated library artifacts `ProSignals_MT5_execution_audit_findings.md` and `ProSignals_Research_Decision_Nov2026.md`, dated 2026-11-04.
