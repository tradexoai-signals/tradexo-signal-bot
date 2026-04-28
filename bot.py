import requests
import datetime
import os
import time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY,
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

COINS = ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","MATIC","LINK","LTC","NEAR","TRX","TON","ATOM"]
MIN_CONFIDENCE = 1
MAX_ACTIVE = 8

def get_klines(symbol, interval="15m", limit=100):
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
            params={"symbol": symbol + "USDT", "interval": interval, "limit": limit}, timeout=10)
        print("  Binance " + symbol + ": " + str(r.status_code))
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or len(data) < 50:
            return None
        return [{"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4]),"volume":float(c[5])} for c in data]
    except Exception as e:
        print("  Binance error: " + str(e))
        return None

def ema(vals, p):
    if len(vals) < p:
        return None
    m = 2.0 / (p + 1)
    v = sum(vals[:p]) / p
    for x in vals[p:]:
        v = (x - v) * m + v
    return v

def rsi(closes, p=14):
    if len(closes) < p + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(abs(min(d, 0)))
    ag = sum(gains[-p:]) / p
    al = sum(losses[-p:]) / p
    if al == 0:
        return 100
    return 100 - (100 / (1 + ag / al))

def macd_hist(closes):
    if len(closes) < 35:
        return None
    mv = []
    for i in range(26, len(closes)):
        ef = ema(closes[:i+1], 12)
        es = ema(closes[:i+1], 26)
        mv.append(ef - es)
    if len(mv) < 9:
        return None
    sl = ema(mv, 9)
    return mv[-1] - sl

def calc_atr(candles, p=14):
    if len(candles) < p + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i-1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-p:]) / p

def get_active():
    r = requests.get(
        SUPABASE_URL + "/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin&order=created_at.desc",
        headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()
    return []

def post_signal(sig):
    r = requests.post(
        SUPABASE_URL + "/rest/v1/bot_signals",
        headers=headers, json=sig, timeout=10)
    print("POST " + sig["coin"] + " " + sig["direction"] + " -> " + str(r.status_code))
    if r.status_code not in (200, 201, 204):
        print("ERR: " + r.text)

def analyze(coin):
    candles = get_klines(coin)
    if not candles or len(candles) < 50:
        print("  no candles for " + coin)
        return None
    closes = [c["close"] for c in candles]
    price = closes[-1]
    rsi_v = rsi(closes)
    hist = macd_hist(closes)
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    atr_v = calc_atr(candles)
    print("  price=" + str(round(price,2)) + " rsi=" + str(round(rsi_v,1) if rsi_v else None) + " hist=" + str(round(hist,4) if hist else None))
    if not all([rsi_v, e20, e50, atr_v]):
        print("  indicators missing")
        return None
    bull = 0
    bear = 0
    if rsi_v < 30:
        bull += 30
    elif rsi_v < 40:
        bull += 15
    elif rsi_v > 70:
        bear += 30
    elif rsi_v > 60:
        bear += 15
    if hist:
        if hist > 0:
            bull += 25
        else:
            bear += 25
    if e20 > e50 and price > e20:
        bull += 25
    elif e20 < e50 and price < e20:
        bear += 25
    rv = sum(c["volume"] for c in candles[-5:]) / 5
    av = sum(c["volume"] for c in candles[-20:]) / 20
    if rv > av * 1.3:
        if bull > bear:
            bull += 10
        else:
            bear += 10
    print("  bull=" + str(bull) + " bear=" + str(bear))
    if bull >= MIN_CONFIDENCE and bull > bear:
        direction = "LONG"
        conf = min(bull, 95)
    elif bear >= MIN_CONFIDENCE and bear > bull:
        direction = "SHORT"
        conf = min(bear, 95)
    else:
        print("  no signal")
        return None
    dec = 2 if price > 100 else (4 if price > 1 else 6)
    if direction == "LONG":
        sl_p = price - (atr_v * 1.5)
        tp1 = price + (atr_v * 2)
        tp2 = price + (atr_v * 3.5)
    else:
        sl_p = price + (atr_v * 1.5)
        tp1 = price - (atr_v * 2)
        tp2 = price - (atr_v * 3.5)
    risk = abs(price - sl_p)
    rr = round(abs(tp1 - price) / risk, 1) if risk > 0 else 1.5
    ap = (atr_v / price) * 100
    rl = "LOW RISK" if ap < 1.5 else ("MEDIUM RISK" if ap < 3 else "HIGH RISK")
    return {
        "coin": coin,
        "direction": direction,
        "confidence": int(conf),
        "entry_low": round(price * 0.998, dec),
        "entry_high": round(price * 1.002, dec),
        "sl": round(sl_p, dec),
        "tp1": round(tp1, dec),
        "tp2": round(tp2, dec),
        "rr": "1:" + str(rr),
        "risk": rl,
        "valid_mins": 60,
        "status": "ACTIVE",
        "source": "ai_bot"
    }

def main():
    print("Bot started: " + str(datetime.datetime.utcnow()))
    print("URL: " + str(SUPABASE_URL))
    print("Key OK: " + str(bool(SUPABASE_KEY)))
    active = get_active()
    active_coins = [s["coin"] for s in active]
    print("Active signals: " + str(len(active)))
    new_sigs = []
    for coin in COINS:
        if coin in active_coins:
            print("Skip: " + coin)
            continue
        print("Scan: " + coin)
        sig = analyze(coin)
        time.sleep(0.3)
        if sig:
            print("  -> " + sig["direction"] + " " + str(sig["confidence"]) + "%")
            new_sigs.append(sig)
    print("Signals found: " + str(len(new_sigs)))
    for sig in new_sigs:
        post_signal(sig)
    if len(active) + len(new_sigs) > MAX_ACTIVE:
        all_a = get_active()
        for old in all_a[MAX_ACTIVE:]:
            requests.patch(
                SUPABASE_URL + "/rest/v1/bot_signals?id=eq." + old["id"],
                headers=headers, json={"status": "CLOSED"}, timeout=10)
            print("Closed: " + old["coin"])
    print("Done!")

main()
