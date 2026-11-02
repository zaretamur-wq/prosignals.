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
from shared_risk import InstrumentSpec, RiskPolicy


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
    minimum = 850 if mode == "forex" else 250
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
            all_signals.append({"bar_index": idx, "side": result["side"],
                                "stop": float(stop), "target": float(target),
                                "score": result["score"]})
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
    p.add_argument("--quantity-step", type=float, required=True)
    p.add_argument("--min-quantity", type=float, required=True)
    p.add_argument("--price-value", type=float, required=True,
                   help="Account-currency value of a 1.0 price move per unit")
    p.add_argument("--commission-per-unit-side", type=float, default=0.0)
    p.add_argument("--slippage", type=float, default=0.0)
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
    trades, equity = run_backtest(bars, decisions, args.capital, instrument,
                                  RiskPolicy(), args.slippage)
    completed = [t for t in trades if t.outcome != "END_OF_TEST"]
    wins = sum(t.pnl > 0 for t in completed)
    result = {
        "market": args.market, "symbol": args.symbol, "candles": len(df),
        "historical_signals": len(decisions), "completed_trades": len(completed),
        "win_rate": wins / len(completed) if completed else None,
        "starting_capital": args.capital, "ending_capital": equity,
        "net_pnl": equity - args.capital,
        "warning": ("Crypto OHLCV replay omits historical derivatives, news blocks, "
                    "TP1/breakeven, BTC cross-asset filter and multiple simultaneous "
                    "positions. All runs require verified point-in-time data, "
                    "spread/margin and instrument specifications before conclusions.")
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
