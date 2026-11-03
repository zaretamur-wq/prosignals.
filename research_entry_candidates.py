"""Offline entry-signal alternatives. Closed-candle information only."""
import pandas as pd

def generate(df, kind="pullback"):
    close=df["close"]
    high=df["high"]
    low=df["low"]
    fast=close.ewm(span=20,adjust=False).mean()
    slow=close.ewm(span=80,adjust=False).mean()
    atr=pd.concat([high-low,(high-close.shift()).abs(),
                   (low-close.shift()).abs()],axis=1).max(axis=1).rolling(14).mean()
    ceiling=high.shift().rolling(20).max()
    floor=low.shift().rolling(20).min()
    if kind=="pullback":
        buy=(fast>slow)&(close.shift()<fast.shift())&(close>fast)
        sell=(fast<slow)&(close.shift()>fast.shift())&(close<fast)
    elif kind=="breakout":
        buy=(close>ceiling)&(close.shift()<=ceiling.shift())&(fast>slow)
        sell=(close<floor)&(close.shift()>=floor.shift())&(fast<slow)
    elif kind=="range":
        width=(ceiling-floor)/close
        flat=((fast-slow).abs()/close)<0.003
        buy=flat&(width<0.035)&(low<=floor+0.2*(ceiling-floor))&(close>close.shift())
        sell=flat&(width<0.035)&(high>=ceiling-0.2*(ceiling-floor))&(close<close.shift())
    else:
        raise ValueError("unknown entry model")
    output=[]
    for i in range(100,len(df)-1):
        if pd.isna(atr.iloc[i]) or atr.iloc[i]<=0:
            continue
        side="BUY" if bool(buy.iloc[i]) else ("SELL" if bool(sell.iloc[i]) else None)
        if side is None:
            continue
        direction=1 if side=="BUY" else -1
        price=float(close.iloc[i])
        distance=1.5*float(atr.iloc[i])
        output.append({"bar_index":i,"side":side,"stop":price-direction*distance,
                       "tp1":price+direction*distance,
                       "tp2":price+direction*2*distance})
    return output
