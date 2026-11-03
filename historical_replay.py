"""Offline historical signal replay for BOTH original ProSignals strategies.

Input: UTC OHLC(V) CSV with time,open,high,low,close[,vol].
No network access and no live orders. Only fully completed candles are scored.
Crypto derivatives/news cannot be reconstructed from OHLCV and are explicitly
neutral/missing, so crypto results are NOT a faithful full-strategy backtest.
"""
import argparse
import json
import math
from pathlib import Path
import pandas as pd
import signals as forex
import crypto_signals as crypto
from shared_backtest import run_backtest
from trade_lifecycle import backtest_lifecycle
from shared_risk import InstrumentSpec, RiskPolicy
from trade_diagnostics import build_report, save_report
from research_regimes import regimes, regime_filter
from research_holdout import compare_holdout
from research_alert_gates import alert_timing_gate
from research_audit import audit_history
from research_costs import cost_sensitivity
from research_forex_sizing import forex_sizing_audit
from research_margin import compare_margin_scenarios
from research_coverage import coverage_report, wilson_win_rate_interval


def load_csv(path, crypto_mode=False):
    df = pd.read_csv(path)
    required = {"time", "open", "high", "low", "close"}
    if not required.issubset(df):
        raise ValueError("CSV needs time,open,high,low,close")
    if crypto_mode and "vol" not in df:
        raise ValueError("Crypto requires vol column")
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="raise")
    if df["time"].duplicated().any() or not df["time"].is_monotonic_increasing:
        raise ValueError("timestamps must be strictly increasing")
    df = df.set_index("time")
    columns = ["open", "high", "low", "close"] + (["vol"] if crypto_mode else [])
    df = df[columns].apply(pd.to_numeric, errors="raise")
    if not all(df[c].notna().all() for c in columns):
        raise ValueError("null market data")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("prices must be positive")
    if ((df.high < df[["open", "close", "low"]].max(axis=1)) |
        (df.low > df[["open", "close"]].min(axis=1))).any():
        raise ValueError("invalid OHLC")
    if crypto_mode and (df.vol < 0).any():
        raise ValueError("negative volume")
    return df


def replay(df, mode, asset="BTC"):
    """Generate historical decisions using original evaluate() and closed bars.

    Historical OHLC cannot reconstruct order books, open interest, funding or
    contemporaneous calendar availability. Crypto scores use missing-data
    points (as the original bot does), not fabricated derivatives.
    """
    if mode not in ("forex", "crypto"):
        raise ValueError("mode must be forex or crypto")
    minimum = 850 if mode == "forex" else 2600
    if len(df) < minimum + 2:
        raise ValueError("not enough history for higher-timeframe indicators")
    all_signals = []
    old_get_data = forex.get_data
    old_h1, old_derivs = crypto.get_h1, crypto.derivs
    missing_derivs = {"funding": None, "oi_chg": None, "ls": None, "book": None}
    try:
        for idx in range(minimum, len(df) - 1):
            prefix = df.iloc[:idx + 1]
            if mode == "forex":
                forex.get_data = lambda ticker, d=prefix: d.copy()
                result = forex.evaluate("HISTORICAL")
                if result is None or not result.get("side"):
                    continue
                stop, target = result["sl"], result["tp"]
                tp1 = None
            else:
                h1 = prefix.resample("1h", origin="epoch").agg({
                    "open": "first", "high": "max", "low": "min",
                    "close": "last", "vol": "sum"
                }).dropna()
                # Provide only historical completed bars; evaluate further
                # excludes its current hourly candle.
                def historical_h1(w, mem, d=h1):
                    out = d.copy()
                    out["hf"] = crypto.ema(out.close, 50)
                    out["hs"] = crypto.ema(out.close, 200)
                    out["adx"], out["pdi"], out["mdi"] = crypto.adx(out)
                    return out
                crypto.get_h1 = historical_h1
                crypto.derivs = lambda w, mem: dict(missing_derivs)
                w = {"name": asset}
                result = crypto.evaluate(w, prefix, {
                    "btc15": None, "h1": {}, "slow": {}, "oi": {}, "last_eval": {}
                })
                if result is None or not result.get("side"):
                    continue
                stop, target = result["sl"], result["tp2"]
                tp1 = result["tp1"]
            all_signals.append({"bar_index": idx, "side": result["side"],
                                "stop": float(stop), "target": float(target),
                                "score": result["score"],
                                "tp1": float(tp1) if tp1 is not None else None,
                                "tp2": float(target)})
    finally:
        forex.get_data = old_get_data
        crypto.get_h1, crypto.derivs = old_h1, old_derivs
    return all_signals


def main():
    p = argparse.ArgumentParser(description="Offline ProSignals research only")
    p.add_argument("--market", choices=["forex", "crypto"], required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", default="BTC")
    p.add_argument("--capital", type=float, default=100.0)
    p.add_argument("--cost-stress", action="store_true",
                   help="Compare zero, baseline, and double transaction costs")
    p.add_argument("--compare-alert-gates", action="store_true",
                   help="Compare crypto cooldown/daily alert gates without live changes")
    p.add_argument("--holdout", action="store_true",
                   help="Chronological 70/30 validation of fixed regime candidates")
    p.add_argument("--compare-regimes", action="store_true",
                   help="In-sample trend/volatility sensitivity; not live strategy")
    p.add_argument("--compare-score-thresholds", action="store_true",
                   help="Exploratory in-sample comparisons, not a tuned live filter")
    p.add_argument("--report-dir", default=None,
                   help="Optional directory for audited trade CSV and diagnostic JSON")
    p.add_argument("--quantity-step", type=float, required=True)
    p.add_argument("--min-quantity", type=float, required=True)
    p.add_argument("--price-value", type=float, required=True,
                   help="Account-currency value of a 1.0 price move per unit")
    p.add_argument("--commission-per-unit-side", type=float, default=0.0)
    p.add_argument("--slippage", type=float, default=0.0)
    p.add_argument("--fee-rate", type=float, default=0.0,
                   help="Per-side fraction of trade notional; 0.001 = 0.1 percent")
    args = p.parse_args()
    if args.market == "forex" and args.symbol == "BTC":
        p.error("specify --symbol for Forex/gold; values vary by broker")
    df = load_csv(args.csv, args.market == "crypto")
    decisions = replay(df, args.market, args.symbol)
    instrument = InstrumentSpec(args.symbol, args.quantity_step,
                                args.min_quantity, args.price_value,
                                args.commission_per_unit_side)
    bars = [{"time": t.isoformat(), **{k: float(v) for k, v in row.items()}}
            for t, row in df.iterrows()]
    if args.market == "crypto":
        trades, equity = backtest_lifecycle(bars, decisions, args.capital,
              instrument, RiskPolicy(), expire_minutes=crypto.EXPIRE_HOURS * 60,
              slippage_fraction=args.slippage, fee_rate=args.fee_rate)
    else:
        trades, equity = run_backtest(bars, decisions, args.capital, instrument,
                                      RiskPolicy(), args.slippage)
    completed = [t for t in trades if t.outcome != "END_OF_TEST"]
    wins = sum(t.pnl > 0 for t in completed)
    pnls = [t.pnl for t in completed]
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = -sum(x for x in pnls if x < 0)
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    running_equity = args.capital
    peak = running_equity
    max_drawdown = 0.0
    for trade in trades:
        running_equity += trade.pnl
        peak = max(peak, running_equity)
        max_drawdown = max(max_drawdown, (peak - running_equity) / peak)
    result = {
        "market": args.market, "symbol": args.symbol, "candles": len(df),
        "historical_signals": len(decisions), "completed_trades": len(completed),
        "win_rate": wins / len(completed) if completed else None,
        "starting_capital": args.capital, "ending_capital": equity,
        "net_pnl": equity - args.capital,
        "profit_factor": profit_factor,
        "max_realized_drawdown_pct": round(100 * max_drawdown, 3),
        "fee_rate_per_side": args.fee_rate,
        "tp1_hits": sum(getattr(t, "tp1_hit", False) for t in trades) if args.market == "crypto" else None,
        "outcomes": {key: sum(t.outcome == key for t in trades) for key in
                     ("STOP", "BREAKEVEN", "TP2", "EXPIRED", "END_OF_TEST")},
         "warning": ("Crypto OHLCV replay omits historical derivatives, news blocks, "
                    "BTC cross-asset filter and multiple simultaneous "
                    "positions. All runs require verified point-in-time data, "
                    "spread/margin and instrument specifications before conclusions.")
    }
    result["data_fidelity_audit"] = audit_history(bars, args.market)
    result["historical_coverage"] = coverage_report(bars, args.market)
    result["win_rate_uncertainty"] = wilson_win_rate_interval(wins, len(completed))
    if args.market == "forex":
        result["forex_sizing_audit"] = forex_sizing_audit(
            bars, decisions, args.capital, instrument)
        result["hypothetical_margin_screen"] = compare_margin_scenarios(
            bars, decisions, args.capital, instrument)
    if args.report_dir:
        report = build_report(bars, decisions, trades, args.capital)
        ledger_path, report_path = save_report(report, args.report_dir, args.symbol)
        result["diagnostics"] = report["summary"]
        result["report_files"] = [ledger_path, report_path]
    if args.compare_score_thresholds:
        # Reuse the SAME bars and original signal candidates. This is an
        # in-sample diagnostic, not evidence of out-of-sample profitability.
        comparisons = {}
        for threshold in (None, 75, 80, 85, 90):
            chosen = decisions if threshold is None else [
                s for s in decisions if s.get("score") is not None
                and float(s["score"]) >= threshold]
            if args.market == "crypto":
                simulated, final_equity = backtest_lifecycle(
                    bars, chosen, args.capital, instrument, RiskPolicy(),
                    expire_minutes=crypto.EXPIRE_HOURS * 60,
                    slippage_fraction=args.slippage, fee_rate=args.fee_rate)
            else:
                simulated, final_equity = run_backtest(
                    bars, chosen, args.capital, instrument, RiskPolicy(),
                    args.slippage)
            finished = [t for t in simulated if t.outcome != "END_OF_TEST"]
            wins_pnl = sum(t.pnl for t in finished if t.pnl > 0)
            losses_pnl = -sum(t.pnl for t in finished if t.pnl < 0)
            comparisons["all" if threshold is None else str(threshold)] = {
                "signals": len(chosen),
                "completed_trades": len(finished),
                "win_rate": (sum(t.pnl > 0 for t in finished) / len(finished)
                             if finished else None),
                "net_pnl": final_equity - args.capital,
                "profit_factor": wins_pnl / losses_pnl if losses_pnl else None,
            }
        result["in_sample_score_comparisons"] = comparisons
        result["comparison_warning"] = (
            "Exploratory on the SAME historical candles. Threshold selection "
            "from this table is overfitting until verified on untouched "
            "forward/out-of-sample data.")
    if args.compare_regimes:
        # Fixed, disclosed parameters. Same dataset for all three alternatives.
        # These are exploratory comparisons, NOT out-of-sample validation.
        historical_regimes = regimes(bars)
        comparisons = {}
        for mode in ("all", "trend", "trend_and_volatility"):
            selected = regime_filter(decisions, historical_regimes, mode)
            if args.market == "crypto":
                sample, ending = backtest_lifecycle(
                    bars, selected, args.capital, instrument, RiskPolicy(),
                    expire_minutes=crypto.EXPIRE_HOURS * 60,
                    slippage_fraction=args.slippage, fee_rate=args.fee_rate)
            else:
                sample, ending = run_backtest(
                    bars, selected, args.capital, instrument, RiskPolicy(),
                    args.slippage)
            finished = [t for t in sample if t.outcome != "END_OF_TEST"]
            gains = sum(t.pnl for t in finished if t.pnl > 0)
            losses = -sum(t.pnl for t in finished if t.pnl < 0)
            comparisons[mode] = {
                "signals":len(selected),
                "completed_trades":len(finished),
                "win_rate":sum(t.pnl > 0 for t in finished)/len(finished) if finished else None,
                "net_pnl":ending-args.capital,
                "profit_factor":gains/losses if losses else None,
            }
        result["in_sample_regime_comparisons"] = comparisons
        result["regime_definition"] = (
            "48 completed-bar lookback, UP/DOWN if return exceeds +/-0.6%, "
            "volatile if RMS log return >=0.2% per bar; no future candles."
        )
        result["regime_warning"] = (
            "In-sample only, parameters not optimized. Cannot justify live "
            "trading without clean point-in-time out-of-sample testing.")
    if args.holdout:
        result["chronological_holdout"] = compare_holdout(
            bars, decisions, args.market, instrument, args.capital,
            slippage=args.slippage, fee_rate=args.fee_rate,
            expire_minutes=crypto.EXPIRE_HOURS * 60)
    if args.cost_stress and args.market == "crypto":
        result["cost_sensitivity"] = cost_sensitivity(
            bars, decisions, args.capital, instrument,
            crypto.EXPIRE_HOURS * 60, args.fee_rate, args.slippage)
    if args.compare_alert_gates and args.market == "crypto":
        gated = alert_timing_gate(bars, decisions,
                                  cooldown_minutes=crypto.COOLDOWN_MIN,
                                  max_daily_alerts=crypto.MAX_ALERTS_PER_DAY)
        gated_trades, gated_equity = backtest_lifecycle(
            bars, gated, args.capital, instrument, RiskPolicy(),
            expire_minutes=crypto.EXPIRE_HOURS * 60,
            slippage_fraction=args.slippage, fee_rate=args.fee_rate)
        gated_completed = [t for t in gated_trades if t.outcome != "END_OF_TEST"]
        result["timing_gate_comparison"] = {
            "original_candidate_signals":len(decisions),
            "cooldown_and_daily_cap_signals":len(gated),
            "gated_completed_trades":len(gated_completed),
            "gated_net_pnl":gated_equity-args.capital,
            "gated_win_rate":(sum(t.pnl>0 for t in gated_completed) /
                              len(gated_completed) if gated_completed else None),
            "warning":"Approximate alert timing only; does not reconstruct news, "
                      "open-signal state or cross-asset filters."
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
