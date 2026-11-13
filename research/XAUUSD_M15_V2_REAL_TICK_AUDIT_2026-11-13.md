# XAUUSD M15 Gold v2 — MT5 Strategy Tester audit (2026-11-13)

**Decision: REJECT candidate. Research only. No profitable Gold bot or 75% win rate verified.**
This note audits the user-supplied `ReportTester-000.xlsx` against the user-requested $100 reference capital, 3% risk ($3 nominal stop risk), 2R target ($6 nominal target), and $6 realized daily loss entry halt.

## Reproduced numbers from MT5 report
- Terminal: 4TLtd-Live; Strategy Tester using 100% real historical ticks. This is **not** evidence of executing a live trading account.
- Expert: `ProSignals_XAUUSD_M15_Demo_v2_3pct_2R`; symbol XAUUSD; M15; 2022-02-16 through 2026-11-03; leverage 1:100; initial deposit $100.
- Inputs: `RiskPercent=3.0`, `RewardMultiple=2.0`, `MaxDailyRealizedLossUSD=6.0`, `MaxEntriesPerDay=3`, `MaxConsecutiveLosses=2`.
- 75 closed trades / 150 entry-exit deals: 18 winning (24.00%) and 57 losing (76.00%).
- Net **-$57.12**, profit factor **0.51671**, maximum equity drawdown **60.89%**, gross winner P&L $61.07, gross loser P&L -$118.19 as printed by MT5.
- Separate deals ledger calculation: trade `Profit` column totals **-$49.20** (positive $63.14, negative -$112.34), with **-$7.92 Swap** across deals, $0 recorded commission. Total = **-$57.12**. Swap charges materially worsened results.
- Largest individual negative trade profit field **-$7.15**. The configured 3% planned stop budget does **not** guarantee each realized outcome stays above -$3 when gaps, fills, and costs intervene.

## Critical chronological coverage defect
Read the **Orders** section rather than inferring from tester end date. Exactly 75 entry orders (each 0.01 lot):
- 2022: **41**; 2023: **29**; 2024: **5**; 2025: **0**; 2026: **0**.
- Last entry: **2024-02-27 07:15:00** (report's server time). The fact that historical ticks extend to November 2026 does not make this a valid 2025-26 test.
- Every closed exit in the Deals section was identified as stop or target: **57 SL**, **18 TP**. The fixed nominal price-distance TP/SL is not enough to produce profitability without a better entry edge.
- Broker Gold min volume reported as 0.01 lot with standard 100 oz per 1.00 lot (thus at min 0.01 lot, approximately $1 P&L per $1.00 gold price movement). A $3 gross risk budget gives at most about $3.00 Gold price-distance to stop **before** commissions, swap, gaps, or slippage. Confirm broker specs and actual `OrderCalcProfit` before relying on this relation.

## Acceptance gates before further user testing
1. **Block any recommendation to reuse this losing v2 EA** for live trading; no 75% / 57% claim.
2. Run a *diagnostic* on 2025-26 data with per-year setup, spread, min-lot, risk/margin, session, daily-stop, and order-reject counters. Separate "no signals" from "signals rejected for min-lot risk"; do not assert cause until logs show it.
3. If $100/3%/0.01-lot combinations are too restrictive to enter recent markets, report **not feasible under specified broker/account** rather than silently increase leverage, lot size, or risk.
4. Any different candidate must beat a simple baseline on a fresh untouched chronological holdout including 2025-26, with correct broker costs and adequate trade count. Profit factor >1 and controlled equity drawdown are necessary; 75% win rate remains aspirational, not guaranteed.
5. Keep `main`, production Telegram, and live execution untouched. Never confuse green GitHub unit tests with profitable MT5 strategy validation.

Source: user-supplied `ReportTester-000.xlsx` analyzed row-by-row on 2026-11-13. No new profitable strategy backtest or MQL5 compilation was performed for this note.
