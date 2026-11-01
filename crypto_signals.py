"""
ProSignals CRYPTO scalper - SIGNAL ONLY (never places trades).
Entry timeframe 5m, confirmation 15m and 1H. Demo / education use only.

Data (all free, no API keys):
  OKX     candles, funding rate, open interest, long/short ratio, order book
  Kraken  candle fallback if OKX is unreachable
  alternative.me  Fear & Greed index
  Google News RSS headlines, community economic calendar (USD high-impact block)

Usage:
  python crypto_signals.py              one pass
  python crypto_signals.py --loop 335   keep running for 335 minutes (5-min bars, polls every 15 s)
  MANUAL=1 python crypto_signals.py     send a status message to Telegram
"""
import os
import sys
import json
import time
import argparse
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests

OKX = "https://www.okx.com"

# ----------------------------- SETTINGS -------------------------------
WATCHLIST = [   # BTC first: alts use BTC's 15m trend as a filter
    {"name": "BTC",  "spot": "BTC-USDT",  "swap": "BTC-USDT-SWAP",  "ccy": "BTC",  "kr": "XBTUSD",  "q": "bitcoin BTC"},
    {"name": "ETH",  "spot": "ETH-USDT",  "swap": "ETH-USDT-SWAP",  "ccy": "ETH",  "kr": "ETHUSD",  "q": "ethereum ETH"},
    {"name": "SOL",  "spot": "SOL-USDT",  "swap": "SOL-USDT-SWAP",  "ccy": "SOL",  "kr": "SOLUSD",  "q": "solana SOL"},
    {"name": "XRP",  "spot": "XRP-USDT",  "swap": "XRP-USDT-SWAP",  "ccy": "XRP",  "kr": "XRPUSD",  "q": "XRP ripple"},
    {"name": "DOGE", "spot": "DOGE-USDT", "swap": "DOGE-USDT-SWAP", "ccy": "DOGE", "kr": "XDGUSD",  "q": "dogecoin DOGE"},
]
MIN_SCORE = 75            # minimum score (0-100) to alert
ATR_SL = 1.2              # minimum stop distance in 5m ATR
ATR_SL_MAX = 2.5          # skip if stop is wider than this
MIN_RISK_PCT = 0.20       # skip if stop is closer than this % (fees would eat the trade)
TP1_R = 1.0
TP2_R = 2.0
COOLDOWN_MIN = 30         # minutes between alerts on the same coin
EXPIRE_HOURS = 4          # an unfinished signal is closed as expired after this
MAX_ALERTS_PER_DAY = 12
POLL_SECONDS = 15
NEWS_MINUTES = 30         # block signals around high-impact USD news
ADX_MIN = 20
BTC_PENALTY = 10          # points removed when an alt signal fights BTC's 15m trend
STATE_FILE = "crypto_state.json"
# -----------------------------------------------------------------------


# ------------------------------ indicators ----------------------------
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


def daily_vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    day = df.index.floor("1D")
    pv = (tp * df["vol"]).groupby(day).cumsum()
    v = df["vol"].groupby(day).cumsum()
    return pv / v.replace(0, np.nan)


# ------------------------------ data ----------------------------------
def get_json(url, params=None, timeout=15):
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


def okx_candles(inst, bar, limit=300):
    j = get_json(OKX + "/api/v5/market/candles", {"instId": inst, "bar": bar, "limit": limit})
    if j.get("code") != "0" or not j.get("data"):
        raise RuntimeError("OKX candles error: " + str(j.get("msg")))
    rows = j["data"][::-1]                      # oldest first
    df = pd.DataFrame(rows).iloc[:, :9]
    df.columns = ["ts", "open", "high", "low", "close", "vol", "volccy", "volquote", "confirm"]
    df.index = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df = df[df["confirm"] == "1"]               # closed bars only
    for c in ["open", "high", "low", "close", "vol"]:
        df[c] = df[c].astype(float)
    return df[["open", "high", "low", "close", "vol"]]


def kraken_candles(pair, minutes):
    j = get_json("https://api.kraken.com/0/public/OHLC", {"pair": pair, "interval": minutes})
    key = [k for k in j["result"] if k != "last"][0]
    rows = j["result"][key][:-1]                # drop the unfinished bar
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "vwap", "vol", "count"])
    df.index = pd.to_datetime(df["ts"].astype("int64"), unit="s", utc=True)
    for c in ["open", "high", "low", "close", "vol"]:
        df[c] = df[c].astype(float)
    return df[["open", "high", "low", "close", "vol"]]


def get_candles(w, tf):
    try:
        return okx_candles(w["spot"], tf, 300), "OKX"
    except Exception as ex:
        print(w["name"], "OKX candles failed:", ex)
    mins = {"5m": 5, "1H": 60}[tf]
    return kraken_candles(w["kr"], mins), "Kraken"


def get_h1(w, mem):
    c = mem["h1"].get(w["name"])
    if c and time.time() - c[0] < 600:
        return c[1]
    df, _ = get_candles(w, "1H")
    df = df.copy()
    df["hf"] = ema(df["close"], 50)
    df["hs"] = ema(df["close"], 200)
    df["adx"], df["pdi"], df["mdi"] = adx(df)
    mem["h1"][w["name"]] = (time.time(), df)
    return df


def derivs(w, mem):
    """Funding, open-interest change (30 min), long/short ratio, order-book imbalance. None = unavailable."""
    d = {"funding": None, "oi_chg": None, "ls": None, "book": None}
    cache = mem["slow"].setdefault(w["name"], {})

    def cached(key, ttl, fn):
        v = cache.get(key)
        if v and time.time() - v[0] < ttl:
            return v[1]
        try:
            val = fn()
        except Exception as ex:
            print(w["name"], key, "unavailable:", ex)
            val = None
        cache[key] = (time.time(), val)
        return val

    d["funding"] = cached("fund", 300, lambda: float(
        get_json(OKX + "/api/v5/public/funding-rate", {"instId": w["swap"]})["data"][0]["fundingRate"]))
    d["ls"] = cached("ls", 300, lambda: float(
        get_json(OKX + "/api/v5/rubik/stat/contracts/long-short-account-ratio",
                 {"ccy": w["ccy"], "period": "5m"})["data"][0][1]))
    try:
        oi = float(get_json(OKX + "/api/v5/public/open-interest",
                            {"instType": "SWAP", "instId": w["swap"]})["data"][0]["oi"])
        hist = mem["oi"].setdefault(w["name"], [])
        hist.append((time.time(), oi))
        hist = [h for h in hist if time.time() - h[0] < 7200]
        mem["oi"][w["name"]] = hist
        old = [h for h in hist if time.time() - h[0] >= 1500]
        if old and old[-1][1] > 0:
            d["oi_chg"] = (oi / old[-1][1] - 1) * 100
    except Exception as ex:
        print(w["name"], "open interest unavailable:", ex)
    try:
        b = get_json(OKX + "/api/v5/market/books", {"instId": w["spot"], "sz": "20"})["data"][0]
        bid = sum(float(x[1]) for x in b["bids"])
        ask = sum(float(x[1]) for x in b["asks"])
        d["book"] = bid / (bid + ask) if (bid + ask) > 0 else None
    except Exception as ex:
        print(w["name"], "order book unavailable:", ex)
    return d


def fear_greed(mem):
    v = mem.get("fng")
    if v and time.time() - v[0] < 3600:
        return v[1]
    val = None
    try:
        x = get_json("https://api.alternative.me/fng/", {"limit": 1})["data"][0]
        val = f"{x['value']} ({x['value_classification']})"
    except Exception as ex:
        print("fear&greed unavailable:", ex)
    mem["fng"] = (time.time(), val)
    return val


def news_blocked(now, mem):
    """High-impact USD economic event within +/- NEWS_MINUTES (CPI, FOMC, NFP move crypto)."""
    c = mem.get("cal")
    if not c or time.time() - c[0] > 600:
        try:
            ev = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=20).json()
        except Exception as ex:
            print("calendar unavailable:", ex)
            ev = []
        mem["cal"] = (time.time(), ev)
        c = mem["cal"]
    for e in c[1]:
        try:
            if e.get("impact") != "High" or e.get("country") != "USD":
                continue
            t = pd.Timestamp(e["date"]).tz_convert("UTC")
            if abs((t - now).total_seconds()) <= NEWS_MINUTES * 60:
                return f"USD {e.get('title')}"
        except Exception:
            continue
    return None


def headlines(q, n=3):
    try:
        url = "https://news.google.com/rss/search?q=" + requests.utils.quote(q) + "&hl=en&gl=US&ceid=US:en"
        root = ET.fromstring(requests.get(url, timeout=20).content)
        return [it.findtext("title") for it in root.iter("item")][:n]
    except Exception as ex:
        print("headlines unavailable:", ex)
        return []


# ------------------------------ scoring -------------------------------
def derivs_score(d, buy, price_chg):
    pts, why, warn = 0, [], []
    f = d["funding"]
    if f is None:
        pts += 2
    elif (f < 0.0004) if buy else (f > -0.0004):
        pts += 5
    else:
        warn.append("crowded funding")
    oi = d["oi_chg"]
    if oi is None:
        pts += 2
    elif oi >= 0.2 and ((price_chg >= 0) if buy else (price_chg <= 0)):
        pts += 5
        why.append("OI rising with price")
    bk = d["book"]
    if bk is None:
        pts += 2
    elif (bk >= 0.55) if buy else (bk <= 0.45):
        pts += 5
        why.append("order book supports")
    return pts, why, warn


def score(A, i, h, m, buy, d):
    sc, why = 0, []
    o, hi, lo, c, vol = A["open"], A["high"], A["low"], A["close"], A["vol"]
    a = A["atr"][i]

    # 1) 1H trend (15)
    ok = (h["hf"] > h["hs"] and h["pdi"] > h["mdi"]) if buy else (h["hf"] < h["hs"] and h["mdi"] > h["pdi"])
    if ok:
        sc += 10
        why.append("1H trend")
        if h["adx"] >= ADX_MIN:
            sc += 5
            why.append("strong ADX")

    # 2) 15m alignment (15)
    if (m["e21"] > m["e50"]) if buy else (m["e21"] < m["e50"]):
        sc += 8
        why.append("15m EMA stack")
    if (m["close"] > m["e50"]) if buy else (m["close"] < m["e50"]):
        sc += 7
        why.append("15m price vs EMA50")

    # 3) VWAP side (10)
    vw = A["vwap"][i]
    if not np.isnan(vw) and ((c[i] > vw) if buy else (c[i] < vw)):
        sc += 10
        why.append("above VWAP" if buy else "below VWAP")

    # 4) Pullback to the 5m value zone (15)
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

    # 5) Momentum (10)
    r, r1 = A["rsi"][i], A["rsi"][i - 1]
    if (45 < r < 68 and r > r1) if buy else (32 < r < 55 and r < r1):
        sc += 5
        why.append("RSI turn")
    hist = A["mm"][i] - A["ms"][i]
    hist1 = A["mm"][i - 1] - A["ms"][i - 1]
    if (hist > hist1) if buy else (hist < hist1):
        sc += 5
        why.append("MACD momentum")

    # 6) Candle trigger + volume (15)
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
    trig = 0
    if engulf or pin:
        trig = 10
        why.append("engulfing" if engulf else "pin bar")
    elif strong:
        trig = 5
        why.append("strong close")
    if trig and vol[i] >= 1.5 * vol[i - 20:i].mean():
        trig += 5
        why.append("volume spike")
    sc += trig

    # 7) Micro structure break (5)
    if buy and c[i] > hi[i - 3:i].max():
        sc += 5
        why.append("structure break")
    if (not buy) and c[i] < lo[i - 3:i].min():
        sc += 5
        why.append("structure break")

    # 8) Derivatives / order flow (15)
    price_chg = c[i] / c[i - 6] - 1
    dp, dwhy, dwarn = derivs_score(d, buy, price_chg)
    sc += dp
    why += dwhy
    return sc, why, dwarn


def evaluate(w, df5, mem):
    if len(df5) < 120:
        return None
    df = df5.copy()
    df["ef"] = ema(df["close"], 21)
    df["es"] = ema(df["close"], 50)
    df["rsi"] = rsi(df["close"])
    df["atr"] = atr(df)
    df["mm"], df["ms"] = macd(df["close"])
    df["vwap"] = daily_vwap(df)

    i = len(df) - 1
    t = df.index[i]

    m15 = df[["open", "high", "low", "close", "vol"]].resample("15min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
    m15["e21"] = ema(m15["close"], 21)
    m15["e50"] = ema(m15["close"], 50)
    p15 = m15[m15.index < t.floor("15min")]          # last COMPLETED 15m bar
    h1 = get_h1(w, mem)
    ph = h1[h1.index < t.floor("1h")]                # last COMPLETED 1H bar
    if p15.empty or ph.empty:
        return None
    m, h = p15.iloc[-1], ph.iloc[-1]
    if m[["e21", "e50"]].isna().any() or h[["hf", "hs", "adx", "pdi", "mdi"]].isna().any():
        return None
    if df[["ef", "es", "rsi", "atr", "mm", "ms"]].iloc[i].isna().any():
        return None

    A = {k: df[k].to_numpy() for k in ["open", "high", "low", "close", "vol", "ef", "es", "rsi", "atr", "mm", "ms", "vwap"]}
    d = derivs(w, mem)
    sb, why_b, warn_b = score(A, i, h, m, True, d)
    ss, why_s, warn_s = score(A, i, h, m, False, d)

    t1h = "UP" if (h["hf"] > h["hs"] and h["pdi"] > h["mdi"]) else ("DOWN" if (h["hf"] < h["hs"] and h["mdi"] > h["pdi"]) else "MIXED")
    t15 = "UP" if m["e21"] > m["e50"] else "DOWN"
    if w["name"] == "BTC":
        mem["btc15"] = t15
    elif mem.get("btc15"):
        if mem["btc15"] == "DOWN":
            sb -= BTC_PENALTY
            warn_b.append("against BTC 15m trend")
        else:
            ss -= BTC_PENALTY
            warn_s.append("against BTC 15m trend")

    out = {"time": t, "close": float(A["close"][i]), "t1h": t1h, "t15": t15, "sb": sb, "ss": ss,
           "d": d, "side": None}
    side = None
    if sb >= MIN_SCORE and sb > ss:
        side = "BUY"
    elif ss >= MIN_SCORE and ss > sb:
        side = "SELL"
    if side:
        a = float(A["atr"][i])
        c = float(A["close"][i])
        if side == "BUY":
            sl = min(float(A["low"][i - 5:i + 1].min()) - 0.2 * a, c - ATR_SL * a)
            risk = c - sl
            tp1, tp2 = c + TP1_R * risk, c + TP2_R * risk
        else:
            sl = max(float(A["high"][i - 5:i + 1].max()) + 0.2 * a, c + ATR_SL * a)
            risk = sl - c
            tp1, tp2 = c - TP1_R * risk, c - TP2_R * risk
        if risk <= ATR_SL_MAX * a and risk / c * 100 >= MIN_RISK_PCT:
            out.update({"side": side, "sl": sl, "tp1": tp1, "tp2": tp2, "risk": risk,
                        "score": sb if side == "BUY" else ss,
                        "why": why_b if side == "BUY" else why_s,
                        "warn": warn_b if side == "BUY" else warn_s})
    return out


# ------------------------------ output --------------------------------
def fmt(x):
    if abs(x) >= 1000:
        return f"{x:,.1f}"
    if abs(x) >= 10:
        return f"{x:.2f}"
    if abs(x) >= 1:
        return f"{x:.4f}"
    return f"{x:.5f}"


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


def deriv_line(d):
    parts = []
    if d["funding"] is not None:
        parts.append(f"funding {d['funding'] * 100:+.3f}%")
    if d["oi_chg"] is not None:
        parts.append(f"OI {d['oi_chg']:+.2f}%/30m")
    if d["ls"] is not None:
        parts.append(f"L/S {d['ls']:.2f}")
    if d["book"] is not None:
        parts.append(f"bids {d['book'] * 100:.0f}%")
    return " | ".join(parts) if parts else "not available"


def load_state():
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
    except Exception:
        st = {}
    st.setdefault("open", [])
    st.setdefault("stats", {})
    for k in ["signals", "tp1", "tp2", "sl", "be", "expired"]:
        st["stats"].setdefault(k, 0)
    st.setdefault("last_alert", {})
    st.setdefault("day", "")
    st.setdefault("day_count", 0)
    return st


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)


def record_line(st):
    s = st["stats"]
    return (f"Record so far: {s['signals']} signals | reached TP1 {s['tp1']} | TP2 {s['tp2']} | "
            f"stop-loss {s['sl']} | back to entry {s['be']} | expired {s['expired']}")


def update_open(state, w, df5, now):
    """Check every open signal of this coin against new 5m candles and report TP1 / TP2 / SL."""
    keep = []
    for s in state["open"]:
        if s["name"] != w["name"]:
            keep.append(s)
            continue
        buy = s["side"] == "BUY"
        t0 = pd.Timestamp(s["time"])
        since = max(t0, pd.Timestamp(s["checked"]))
        closed = False
        for ts, b in df5[df5.index > since].iterrows():
            s["checked"] = ts.isoformat()
            hi, lo = b["high"], b["low"]
            ev = None
            if s["stage"] == 0:
                if (lo <= s["sl"]) if buy else (hi >= s["sl"]):
                    ev = "SL"
                elif (hi >= s["tp1"]) if buy else (lo <= s["tp1"]):
                    ev = "TP1"
            else:
                if (lo <= s["entry"]) if buy else (hi >= s["entry"]):
                    ev = "BE"
                elif (hi >= s["tp2"]) if buy else (lo <= s["tp2"]):
                    ev = "TP2"
            if not ev:
                continue
            st = state["stats"]
            tag = f"{w['name']} {s['side']}"
            if ev == "TP1":
                st["tp1"] += 1
                s["stage"] = 1
                notify(f"✅ {tag}: TP1 reached (+{TP1_R:g}R). Move your stop to entry {fmt(s['entry'])}.\n" + record_line(state))
                continue
            closed = True
            if ev == "TP2":
                st["tp2"] += 1
                notify(f"🎯 {tag}: TP2 reached (+{TP2_R:g}R).\n" + record_line(state))
            elif ev == "SL":
                st["sl"] += 1
                notify(f"❌ {tag}: stop-loss hit (-1R).\n" + record_line(state))
            else:
                st["be"] += 1
                notify(f"➖ {tag}: price came back to entry after TP1.\n" + record_line(state))
            break
        if not closed and now - t0 > pd.Timedelta(hours=EXPIRE_HOURS):
            state["stats"]["expired"] += 1
            closed = True
            notify(f"⌛ {w['name']} {s['side']}: signal expired after {EXPIRE_HOURS}h without finishing.\n" + record_line(state))
        if not closed:
            keep.append(s)
    state["open"] = keep


def cycle(state, mem, manual=False):
    now = pd.Timestamp.now(tz="UTC")
    today = now.strftime("%Y-%m-%d")
    if state["day"] != today:
        state["day"], state["day_count"] = today, 0
    summary = []

    for w in WATCHLIST:
        try:
            df5, src = get_candles(w, "5m")
        except Exception as ex:
            print(w["name"], "no data:", ex)
            continue
        mem["src"] = src
        update_open(state, w, df5, now)

        last_bar = df5.index[-1]
        if not manual and mem["last_eval"].get(w["name"]) == last_bar:
            continue
        mem["last_eval"][w["name"]] = last_bar
        try:
            r = evaluate(w, df5, mem)
        except Exception as ex:
            print(w["name"], "evaluate error:", ex)
            continue
        if r is None:
            continue
        summary.append(f"{w['name']}: 1H {r['t1h']} | 15m {r['t15']} | BUY {r['sb']} / SELL {r['ss']} | {deriv_line(r['d'])}")
        if not r["side"]:
            continue

        fresh = (now - (last_bar + pd.Timedelta(minutes=5))) <= pd.Timedelta(minutes=7)
        la = state["last_alert"].get(w["name"])
        cooling = la and (now - pd.Timestamp(la)) < pd.Timedelta(minutes=COOLDOWN_MIN)
        has_open = any(s["name"] == w["name"] for s in state["open"])
        if (not fresh) or cooling or has_open or state["day_count"] >= MAX_ALERTS_PER_DAY:
            continue
        blocked = news_blocked(now, mem)
        if blocked:
            print(w["name"], "signal blocked by news:", blocked)
            continue

        buy = r["side"] == "BUY"
        e, sl, tp1, tp2 = r["close"], r["sl"], r["tp1"], r["tp2"]
        skip_beyond = e + 0.3 * r["risk"] if buy else e - 0.3 * r["risk"]
        hl = headlines(w["q"])
        fng = fear_greed(mem)
        msg = (f"{'🟢 BUY' if buy else '🔴 SELL'} {w['name']} (5m scalp)\n"
               f"Score {r['score']}/100 | 1H {r['t1h']} | 15m {r['t15']}\n"
               f"Entry: {fmt(e)}\n"
               f"Stop-loss: {fmt(sl)} ({abs(e - sl) / e * 100:.2f}%)\n"
               f"TP1: {fmt(tp1)} (1R) -> then move stop to entry\n"
               f"TP2: {fmt(tp2)} (2R)\n"
               f"Skip if price is already beyond {fmt(skip_beyond)}\n"
               f"Why: {', '.join(r['why'])}\n"
               + (f"Warnings: {', '.join(r['warn'])}\n" if r["warn"] else "")
               + f"Derivatives: {deriv_line(r['d'])}\n"
               + (f"Fear & Greed: {fng}\n" if fng else "")
               + "News window: clear\n"
               + ("Headlines:\n- " + "\n- ".join(hl) + "\n" if hl else "")
               + "Demo analysis only. Not financial advice. Valid about 15 min.")
        notify(msg)
        state["open"].append({"name": w["name"], "side": r["side"], "time": r["time"].isoformat(),
                              "checked": r["time"].isoformat(), "entry": e, "sl": sl, "tp1": tp1,
                              "tp2": tp2, "stage": 0})
        state["stats"]["signals"] += 1
        state["last_alert"][w["name"]] = now.isoformat()
        state["day_count"] += 1

    if manual:
        fng = fear_greed(mem)
        notify(f"ProSignals CRYPTO test OK (data: {mem.get('src', '?')})\n" + "\n".join(summary)
               + (f"\nFear & Greed: {fng}" if fng else "") + "\n" + record_line(state))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=float, default=0, help="minutes to keep running")
    args = ap.parse_args()
    manual = os.environ.get("MANUAL") == "1"
    state = load_state()
    mem = {"h1": {}, "slow": {}, "oi": {}, "last_eval": {}}

    if manual or args.loop <= 0:
        cycle(state, mem, manual)
        save_state(state)
        return

    end = time.time() + args.loop * 60
    last_save = time.time()
    while time.time() < end:
        t = time.time()
        try:
            cycle(state, mem)
        except Exception as ex:
            print("cycle error:", ex)
        if time.time() - last_save > 600:
            save_state(state)
            last_save = time.time()
        time.sleep(max(1, POLL_SECONDS - (time.time() - t)))
    save_state(state)


if __name__ == "__main__":
    sys.exit(main())
