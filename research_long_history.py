"""Fetch longer public market history for research, without orders or secrets."""
import argparse
import json
import time
from pathlib import Path
import pandas as pd
import requests
import yfinance as yf
from research_import import validate_history_csv

def crypto_history(symbol, count=50000):
    if symbol not in ("BTC","ETH") or not 1<=count<=60000:
        raise ValueError("unsupported symbol/count")
    session=requests.Session()
    rows={}
    cursor=None
    for i in range((count+99)//100+12):
        params={"instId":symbol+"-USDT","bar":"5m","limit":"100"}
        if cursor is not None:
            params["after"]=str(cursor)
        for attempt in range(5):
            try:
                resp=session.get("https://www.okx.com/api/v5/market/history-candles",
                                 params=params,timeout=30)
                resp.raise_for_status()
                payload=resp.json()
                if payload.get("code")!="0":
                    raise RuntimeError("OKX: "+str(payload.get("msg")))
                batch=payload.get("data") or []
                break
            except (requests.RequestException,ValueError):
                if attempt==4:
                    raise
                time.sleep(2**attempt)
        if not batch:
            break
        for item in batch:
            if item[8]=="1":
                rows[int(item[0])]=item[1:6]
        oldest=min(int(item[0]) for item in batch)
        if cursor is not None and oldest>=cursor:
            raise RuntimeError("pagination stalled")
        cursor=oldest
        if len(rows)>=count or len(batch)<100:
            break
        time.sleep(0.12)
    if len(rows)<2:
        raise RuntimeError("no usable OKX candles")
    items=sorted(rows.items())[-count:]
    df=pd.DataFrame([[pd.to_datetime(ts,unit="ms",utc=True),*values]
                     for ts,values in items],
                    columns=["time","open","high","low","close","vol"])
    for col in ["open","high","low","close","vol"]:
        df[col]=pd.to_numeric(df[col])
    return df

def daily_history(symbol):
    tickers={"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X",
             "USDJPY":"JPY=X","GOLD":"GC=F"}
    if symbol not in tickers:
        raise ValueError("unsupported symbol")
    raw=yf.download(tickers[symbol],period="15y",interval="1d",
                    auto_adjust=True,progress=False,threads=False)
    if raw.empty:
        raise RuntimeError("Yahoo returned no daily data")
    if isinstance(raw.columns,pd.MultiIndex):
        raw.columns=raw.columns.get_level_values(0)
    df=raw.rename(columns=str.lower)[["open","high","low","close"]].dropna().reset_index()
    df.rename(columns={df.columns[0]:"time"},inplace=True)
    df["time"]=pd.to_datetime(df["time"],utc=True)
    # A daily bar stamped today may be incomplete.
    now=pd.Timestamp.now(tz="UTC")
    df=df[df["time"]<now.normalize()].copy()
    if len(df)<2:
        raise RuntimeError("insufficient closed daily bars")
    return df

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--market",choices=["crypto","forex"],required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--count",type=int,default=50000)
    args=p.parse_args()
    df=(crypto_history(args.symbol,args.count) if args.market=="crypto"
        else daily_history(args.symbol))
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False)
    # Daily market closures are expected; validate schema independently.
    if args.market=="crypto":
        audit=validate_history_csv(path,"crypto","5m",min_days=0)
    else:
        audit={"warning":"Daily market data: exchange holiday/weekend "
                         "closures require calendar-aware audit."}
    result={"market":args.market,"symbol":args.symbol,"bars":len(df),
            "first_utc":str(df["time"].iloc[0]),
            "last_utc":str(df["time"].iloc[-1]),
            "span_days":round((df["time"].iloc[-1]-df["time"].iloc[0]).total_seconds()/86400,2),
            "source":"OKX 5m spot" if args.market=="crypto" else
                     "Yahoo Finance daily; GOLD is GC=F futures proxy, not spot XAUUSD",
            "audit":audit}
    path.with_suffix(".json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if args.market=="crypto" and not audit["ready_for_research"]:
        raise RuntimeError("Crypto gaps detected; retained data for inspection")

if __name__=="__main__":
    main()
