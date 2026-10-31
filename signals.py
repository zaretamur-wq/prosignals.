"""
ProSignals cloud bot - SIGNAL ONLY (never places trades).
Demo / education use. Not financial advice.
"""
import os
import sys
import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ----------------------------- SETTINGS -------------------------------
WATCHLIST = [
    {"name": "EURUSD", "yf": "EURUSD=X", "ccy": ["EUR", "USD"], "q": "EURUSD euro dollar"},
    {"name": "GBPUSD", "yf": "GBPUSD=X", "ccy": ["GBP", "USD"], "q": "GBPUSD pound dollar"},
    {"name": "USDJPY", "yf": "JPY=X",    "ccy": ["USD", "JPY"], "q": "USDJPY yen dollar"},
    {"name": "XAUUSD (Gold)", "yf": "GC=F", "ccy": ["USD"], "q": "gold price"},
    {"name": "BTCUSD", "yf": "BTC-USD",  "ccy": ["USD"], "q": "bitcoin"},
    {"name": "ETHUSD", "yf": "ETH-USD",  "ccy": ["USD"], "q": "ethereum"},
]
MIN_SCORE = 75
RR = 2.0
SL_ATR_MIN = 1.0
SL_ATR_MAX = 3.0
SWING_BARS = 5
COOLDOWN_HOURS = 5
NEWS_MINUTES = 30
ADX_MIN = 20
STATE_FILE = "state.json"
# -----------------------------------------------------------------------


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = rma(up, n) / rma(dn, n).replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return rma(tr, n)


def macd(c, f=12, s=26, sg=9):
    m = ema(c, f) - ema(c, s)
    return m, ema(m, sg)


def adx(df, n=14):
    up = df["high"].diff()
    dn = -df["low"].diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    a = atr(df, n)
    pdi = 100 * rma(pdm, n) / a
    mdi = 100 * rma(mdm, n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx, n), pdi, mdi


def get_data(ticker):
    raw = yf.download(ticker, period="300d", interval="1h", auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    now = pd.Timestamp.now(tz="UTC")
    if len(df) and df.index[-1] + pd.Timedelta(hours=1) > now:
        df = df.iloc[:-1]
    return df


def score(A, i, h, buy):
    sc = 0
    why = []
    o, hi, lo, c = A["open"], A["high"], A["low"], A["close"]
    a = A["atr"][i]

    htf_ok = (h["hf"] > h["hs"] and h["pdi"] > h["mdi"]) if buy else (h["hf"] < h["hs"] and h["mdi"] > h["pdi"])
    if htf_ok:
        sc += 15
        why.append("4H trend")
        if h["adx"] >= ADX_MIN:
            sc += 10
            why.append("strong ADX")

    ef, es = A["ef"][i], A["es"][i]
    if (ef > es) if buy else (ef < es):
        sc += 10
        why.append("EMA stack")
    if (c[i] > es) if buy else (c[i] < es):
        sc += 10
        why.append("price vs EMA50")

    pb = False
    for k in range(3):
        e = A["ef"][i - k]
        if buy and lo[i - k] <= e + 0.25 * a:
            pb = True
        if (not buy) and hi[i - k] >= e - 0.25 * a:
            pb = True
    if pb:
        sc += 15
        why.append("pullback to value")

    r, r1 = A["rsi"][i], A["rsi"][i - 1]
    rsi_ok = (45 < r < 68 and r > r1) if buy else (32 < r < 55 and r < r1)
    if rsi_ok:
        sc += 8
        why.append("RSI turn")
    hist = A["mm"][i] - A["ms"][i]
    hist1 = A["mm"][i - 1] - A["ms"][i - 1]
    if (hist > hist1) if buy else (hist < hist1):
        sc += 7
        why.append("MACD momentum")

    body = abs(c[i] - o[i])
    rng = max(hi[i] - lo[i], 1e-12)
    up_w = hi[i] - max(o[i], c[i])
    lo_w = min(o[i], c[i]) - lo[i]
    if buy:
        engulf = c[i] > o[i] and c[i - 1] < o[i - 1] and c[i] > o[i - 1] and o[i] <= c[i - 1]
        pin = lo_w >= 2 * body and lo_w >= 0.4 * rng and c[i] > lo[i] + 0.6 * rng
        strong = c[i] > o[i] and body >= 0.6 * rng and c[i] > hi[i - 1]
    else:
        engulf = c[i] < o[i] and c[i - 1] > o[i - 1] and c[i] < o[i - 1] and o[i] >= c[i - 1]
        pin = up_w >= 2 * body and up_w >= 0.4 * rng and c[i] < hi[i] - 0.6 * rng
        strong = c[i] < o[i] and body >= 0.6 * rng and c[i] < lo[i - 1]
    if engulf or pin:
        sc += 15
        why.append("engulfing" if engulf else "pin bar")
    elif strong:
        sc += 8
        why.append("strong close")

    if buy and c[i] > hi[i - 3:i].max():
        sc += 10
        why.append("structure break")
    if (not buy) and c[i] < lo[i - 3:i].min():
        sc += 10
        why.append("structure break")

    return sc, why


def evaluate(ticker):
    df = get_data(ticker)
    if df is None or len(df) < 120:
        return None
    df["ef"] = ema(df["close"], 21)
    df["es"] = ema(df["close"], 50)
    df["rsi"] = rsi(df["close"])
    df["atr"] = atr(df)
    df["mm"], df["ms"] = macd(df["close"])

    htf = df[["open", "high", "low", "close"]].resample("4h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    htf["hf"] = ema(htf["close"], 50)
    htf["hs"] = ema(htf["close"], 200)
    htf["adx"], htf["pdi"], htf["mdi"] = adx(htf)
    if len(htf) < 210:
        return None

    i = len(df) - 1
    t = df.index[i]
    prior = htf[htf.index < t.floor("4h")]
    if prior.empty:
        return None
    h = prior.iloc[-1]
    if h[["hf", "hs", "adx", "pdi", "mdi"]].isna().any() or df[["ef", "es", "rsi", "atr", "mm", "ms"]].iloc[i].isna().any():
        return None

    A = {k: df[k].to_numpy() for k in ["open", "high", "low", "close", "ef", "es", "rsi", "atr", "mm", "ms"]}
    sb, why_b = score(A, i, h, True)
    ss, why_s = score(A, i, h, False)

    trend = "UP" if (h["hf"] > h["hs"] and h["pdi"] > h["mdi"]) else ("DOWN" if (h["hf"] < h["hs"] and h["mdi"] > h["pdi"]) else "MIXED")
    out = {"time": t, "close": float(A["close"][i]), "trend": trend, "sb": sb, "ss": ss, "side": None}

    side = None
    if sb >= MIN_SCORE and sb > ss:
        side = "BUY"
    elif ss >= MIN_SCORE and ss > sb:
        side = "SELL"
    if side:
        a = float(A["atr"][i])
        c = float(A["close"][i])
        if side == "BUY":
            sl = min(float(A["low"][i - SWING_BARS + 1:i + 1].min()) - 0.2 * a, c - SL_ATR_MIN * a)
            risk = c - sl
            tp = c + RR * risk
        else:
            sl = max(float(A["high"][i - SWING_BARS + 1:i + 1].max()) + 0.2 * a, c + SL_ATR_MIN * a)
            risk = sl - c
            tp = c - RR * risk
        if risk <= SL_ATR_MAX * a:
            out.update({"side": side, "sl": sl, "tp": tp, "score": sb if side == "BUY" else ss,
                        "why": why_b if side == "BUY" else why_s})
    return out


def news_blocked(currencies, now):
    try:
        ev = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=20).json()
        for e in ev:
            if e.get("impact") != "High" or e.get("country") not in currencies:
                continue
            t = pd.Timestamp(e["date"]).tz_convert("UTC")
            if abs((t - now).total_seconds()) <= NEWS_MINUTES * 60:
                return f"{e.get('country')} {e.get('title')}"
    except Exception as ex:
        print("calendar unavailable:", ex)
    return None


def headlines(q, n=3):
    try:
        url = "https://news.google.com/rss/search?q=" + requests.utils.quote(q) + "&hl=en&gl=US&ceid=US:en"
        root = ET.fromstring(requests.get(url, timeout=20).content)
        return [it.findtext("title") for it in root.iter("item")][:n]
    except Exception as ex:
        print("headlines unavailable:", ex)
        return []


def fmt(x):
    return f"{x:.5f}" if abs(x) < 10 else f"{x:.2f}"


def notify(msg):
    print(msg)
    tok, cid = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
    if tok and cid:
        try:
            requests.get(f"https://api.telegram.org/bot{tok}/sendMessage",
                         params={"chat_id": cid, "text": msg}, timeout=20)
        except Exception as ex:
            print("telegram failed:", ex)
    ph, key = os.environ.get("WA_PHONE"), os.environ.get("WA_KEY")
    if ph and key:
        try:
            requests.get("https://api.callmebot.com/whatsapp.php",
                         params={"phone": ph, "text": msg, "apikey": key}, timeout=20)
        except Exception as ex:
            print("whatsapp failed:", ex)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    manual = os.environ.get("MANUAL") == "1"
    state = load_state()
    now = pd.Timestamp.now(tz="UTC")
    summary = []

    for w in WATCHLIST:
        try:
            r = evaluate(w["yf"])
        except Exception as ex:
            print(w["name"], "error:", ex)
            continue
        if r is None:
            print(w["name"], "not enough data")
            continue
        summary.append(f"{w['name']}: 4H {r['trend']} | BUY {r['sb']} / SELL {r['ss']}")
        if not r["side"]:
            continue

        fresh = (now - (r["time"] + pd.Timedelta(hours=1))) <= pd.Timedelta(minutes=100)
        last = state.get(w["yf"])
        recent = last and (r["time"] - pd.Timestamp(last)) < pd.Timedelta(hours=COOLDOWN_HOURS)
        if (not fresh and not manual) or recent:
            continue
        blocked = news_blocked(w["ccy"], now)
        if blocked:
            print(w["name"], "signal blocked by news:", blocked)
            continue

        icon = "🟢 BUY" if r["side"] == "BUY" else "🔴 SELL"
        hl = headlines(w["q"])
        msg = (f"{icon} {w['name']} (1H)\n"
               f"Score {r['score']}/100 | 4H trend {r['trend']}\n"
               f"Entry {fmt(r['close'])}\nSL {fmt(r['sl'])}\nTP {fmt(r['tp'])} (1:{RR:g})\n"
               f"Why: {', '.join(r['why'])}\n"
               f"News window: clear\n"
               + ("Latest headlines:\n- " + "\n- ".join(hl) + "\n" if hl else "")
               + "Demo analysis only. Not financial advice.")
        notify(msg)
        state[w["yf"]] = r["time"].isoformat()

    if manual:
        notify("ProSignals test run OK\n" + "\n".join(summary))

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)


if __name__ == "__main__":
    sys.exit(main())
