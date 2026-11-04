"""Research-only checks for a collection of independently backtested symbols.

This is NOT a portfolio simulator: trades may overlap and capital/risk
is not shared. Never add independent equity curves and call it portfolio P&L.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
from forex_backtest import backtest

SUPPORTED = ("EURUSD", "GBPUSD")


def run_independent_backtests(files, **kwargs):
    """Evaluate each supported symbol separately with the same initial cash."""
    if not files:
        raise ValueError("At least one CSV is required")
    results = {}
    for symbol, path in files.items():
        if symbol not in SUPPORTED:
            raise ValueError(f"{symbol} has no verified USD pip-value model")
        results[symbol] = backtest(pd.read_csv(path), symbol=symbol, **kwargs)
    return {
        "mode": "independent_per_symbol_not_portfolio",
        "results": results,
        "warning": ("Each backtest uses its own starting cash and daily guard. "
                    "Do not aggregate returns or treat these as shared-account trades. "
                    "No commissions, swaps, margin, or broker execution modeled."),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eurusd", type=Path)
    parser.add_argument("--gbpusd", type=Path)
    parser.add_argument("--risk-pct", type=float, default=0.03)
    args = parser.parse_args()
    files = {symbol: getattr(args, symbol.lower()) for symbol in SUPPORTED
             if getattr(args, symbol.lower()) is not None}
    print(json.dumps(run_independent_backtests(files, risk_pct=args.risk_pct), indent=2))
