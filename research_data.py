"""Fetch a limited real historical sample for OFFLINE research.
Never uses account credentials or sends orders. Data download can fail or be
rate-limited; a failed download must fail the test rather than synthesize trades.
"""
import argparse
import time
from pathlib import Path
import pandas as pd
import requests
import yfinance as yf


def crypto_okx(symbol, count=3000):
    if count < 1 or count > 10000:
        raise ValueError("count outside research limit")
    pair = f"{symbol}-USDT"
    cursor = None
    rows = {}
    session = requests.Session()
    for _ in range((count + 99) // 100 + 4):
        params = {"instId": pair, "bar": "5m", "limit": "100"}
        if cursor is not None:
            params["after"] = str(cursor)
        resp = session.get("https://www.okx.com/api/v5/market/history-candles",
                           params=params, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != "0" or not payload.get("data"):
            raise RuntimeError(f"OKX historical candles unavailable: {payload.get('msg')}")
        batch = payload["data"]
        for row in batch:
            if row[8] == "1":
                rows[int(row[0])] = (row[1], row[2], row[3], row[4], row[5])
        oldest = min(int(row[0]) for row in batch)
        if cursor is not None and oldest >= cursor:
            raise RuntimeError("pagination did not advance")
        cursor = oldest
        if len(rows) >= count or len(batch) < 100:
            break
        time.sleep(0.1)
    if len(rows) < count:
        raise RuntimeError(f"Only {len(rows)} closed candles, expected {count}")
    items = sorted(rows.items())[-count:]
    frame = pd.DataFrame(
        [[pd.to_datetime(ts, unit="ms", utc=True), *values] for ts, values in items],
        columns=["time", "open", "high", "low", "close", "vol"])
    for col in ["open", "high", "low", "close", "vol"]:
        frame[col] = frame[col].astype(float)
    if (frame["time"].diff().iloc[1:] != pd.Timedelta(minutes=5)).any():
        raise RuntimeError("missing 5-minute bars")
    return frame


def forex_yahoo(symbol, period="59d"):
    tickers = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
               "USDJPY": "JPY=X", "GOLD": "GC=F"}
    if symbol not in tickers:
        raise ValueError("unsupported research symbol")
    raw = yf.download(tickers[symbol], period=period, interval="1h",
                      auto_adjust=True, progress=False, threads=False)
    if raw.empty:
        raise RuntimeError("Yahoo returned no historical data")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.lower)
    df = raw[["open", "high", "low", "close"]].dropna().reset_index()
    df.rename(columns={df.columns[0]: "time"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    # Yahoo's most recent hourly bar may still be open.
    if not df.empty and df["time"].iloc[-1] + pd.Timedelta(hours=1) > pd.Timestamp.now(tz="UTC"):
        df = df.iloc[:-1]
    if len(df) < 852:
        raise RuntimeError(f"Only {len(df)} Forex hourly candles, minimum 852")
    return df


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--market", choices=["forex","crypto"], required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--count", type=int, default=3000)
    args = p.parse_args()
    df = crypto_okx(args.symbol, args.count) if args.market == "crypto" else forex_yahoo(args.symbol)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Fetched real {args.symbol} {args.market}: {len(df)} bars "
          f"from {df.time.iloc[0]} to {df.time.iloc[-1]}")
    print(f"Research CSV: {path}")


if __name__=="__main__":
    main()
