import os
import time
import requests
from datetime import datetime

# ================= CONFIG =================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
raise Exception("Missing SUPABASE ENV variables")

print("🚀 Bot started at", datetime.now())

COINS = ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","MATIC","LINK","LTC","NEAR","TRX","TON","ATOM"]
MIN_CONFIDENCE = 45
MAX_ACTIVE = 8

HEADERS = {
"apikey": SUPABASE_KEY,
"Authorization": f"Bearer {SUPABASE_KEY}",
"Content-Type": "application/json"
}

# ================= BINANCE =================

def get_klines(symbol):
try:
url = "https://api1.binance.com/api/v3/klines"
params = {"symbol": symbol+"USDT", "interval": "15m", "limit": 100}
r = requests.get(url, params=params, timeout=10)

```
    if r.status_code != 200:
        print("Binance:", symbol, r.status_code)
        return None

    return [{
        "open": float(c[1]),
        "high": float(c[2]),
        "low": float(c[3]),
        "close": float(c[4]),
        "volume": float(c[5])
    } for c in r.json()]

except Exception as e:
    print("Klines error:", e)
    return None
```

# ================= INDICATORS =================

def ema(vals, p):
if len(vals) < p:
return None
m = 2/(p+1)
v = sum(vals[:p])/p
for x in vals[p:]:
v = (x-v)*m+v
return v

def rsi(closes, p=14):
if len(closes) < p+1:
return None
g, l = [], []
for i in range(1, len(closes)):
d = closes[i] - closes[i-1]
g.append(max(d, 0))
l.append(abs(min(d, 0)))
ag = sum(g[-p:])/p
al = sum(l[-p:])/p
return 100 if al == 0 else 100 - (100/(1+ag/al))

def macd_hist(closes):
if len(closes) < 35:
return None
mv = []
for i in range(26, len(closes)):
ef = ema(closes[:i+1], 12)
es = ema(closes[:i+1], 26)
mv.append(ef-es)
if len(mv) < 9:
return None
sl = ema(mv, 9)
return mv[-1] - sl

def atr(candles, p=14):
if len(candles) < p+1:
return None
trs = []
for i in range(1, len(candles)):
h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
trs.append(max(h-l, abs(h-pc), abs(l-pc)))
return sum(trs[-p:])/p

# ================= ANALYSIS =================

def analyze(coin):
candles = get_klines(coin)
if not candles or len(candles) < 50:
return None

```
closes = [c["close"] for c in candles]
price = closes[-1]

rsi_v = rsi(closes)
hist = macd_hist(closes)
e20 = ema(closes, 20)
e50 = ema(closes, 50)
atr_v = atr(candles)

if not all([rsi_v, e20, e50, atr_v]):
    return None

bull = bear = 0

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

rv = sum(c["volume"] for c in candles[-5:])/5
av = sum(c["volume"] for c in candles[-20:])/20

if rv > av*1.3:
    if bull > bear:
        bull += 10
    else:
        bear += 10

if bull >= MIN_CONFIDENCE and bull > bear:
    direction, conf = "LONG", min(bull, 95)
elif bear >= MIN_CONFIDENCE and bear > bull:
    direction, conf = "SHORT", min(bear, 95)
else:
    return None

dec = 2 if price > 100 else (4 if price > 1 else 6)

if direction == "LONG":
    sl_p = price-(atr_v*1.5)
    tp1 = price+(atr_v*2)
    tp2 = price+(atr_v*3.5)
else:
    sl_p = price+(atr_v*1.5)
    tp1 = price-(atr_v*2)
    tp2 = price-(atr_v*3.5)

risk = abs(price-sl_p)
rr = round(abs(tp1-price)/risk, 1) if risk > 0 else 1.5

return {
    "coin": coin,
    "direction": direction,
    "confidence": int(conf),
    "entry_low": round(price*0.998, dec),
    "entry_high": round(price*1.002, dec),
    "sl": round(sl_p, dec),
    "tp1": round(tp1, dec),
    "tp2": round(tp2, dec),
    "rr": "1:"+str(rr),
    "risk": "AUTO",
    "valid_mins": 60,
    "status": "ACTIVE",
    "source": "ai_bot"
}
```

# ================= DATABASE =================

def post_signal(sig):
try:
url = SUPABASE_URL + "/rest/v1/bot_signals"
r = requests.post(url, headers=HEADERS, json=sig, timeout=10)

```
    print("POST:", sig["coin"], sig["direction"], "→", r.status_code)

    if r.status_code not in (200, 201, 204):
        print("RESPONSE:", r.text)

except Exception as e:
    print("Post error:", e)
```

def get_active():
try:
url = SUPABASE_URL + "/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin&order=created_at.desc"
r = requests.get(url, headers=HEADERS, timeout=10)
return r.json() if r.status_code == 200 else []
except:
return []

# ================= MAIN =================

print("Fetching active signals...")
active = get_active()
active_coins = [s["coin"] for s in active]

new_sigs = []

for coin in COINS:
if coin in active_coins:
print("Skip:", coin)
continue

```
print("Scanning:", coin)
sig = analyze(coin)
time.sleep(0.2)

if sig:
    print("Signal:", sig["direction"], sig["confidence"], "%")
    new_sigs.append(sig)
```

print("Total signals:", len(new_sigs))

for sig in new_sigs:
post_signal(sig)

print("✅ Done")
