import os
import time
import requests
from datetime import datetime

# ================= CONFIG =================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
raise Exception("Missing SUPABASE ENV variables")

print("Started:", datetime.now())
print("Supabase URL:", SUPABASE_URL)

COINS = ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","MATIC","LINK","LTC","NEAR","TRX","TON","ATOM"]
MIN_CONFIDENCE = 45
MAX_ACTIVE = 8

HEADERS = {
"apikey": SUPABASE_KEY,
"Authorization": f"Bearer {SUPABASE_KEY}",
"Content-Type": "application/json",
"Prefer": "return=minimal"
}

# ================= DATA =================

def get_klines(symbol, interval="15m", limit=100):
try:
url = "https://api.binance.com/api/v3/klines"
params = {"symbol": symbol+"USDT", "interval": interval, "limit": limit}
r = requests.get(url, params=params, timeout=10)

```
    if r.status_code != 200:
        print(f"Binance error {symbol}:", r.text)
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

def ema(vals, period):
if len(vals) < period:
return None
multiplier = 2 / (period + 1)
ema_val = sum(vals[:period]) / period
for price in vals[period:]:
ema_val = (price - ema_val) * multiplier + ema_val
return ema_val

def rsi(closes, period=14):
if len(closes) < period + 1:
return None

```
gains, losses = [], []
for i in range(1, len(closes)):
    diff = closes[i] - closes[i - 1]
    gains.append(max(diff, 0))
    losses.append(abs(min(diff, 0)))

avg_gain = sum(gains[-period:]) / period
avg_loss = sum(losses[-period:]) / period

if avg_loss == 0:
    return 100

rs = avg_gain / avg_loss
return 100 - (100 / (1 + rs))
```

def macd_hist(closes):
if len(closes) < 35:
return None

```
macd_vals = []
for i in range(26, len(closes)):
    fast = ema(closes[:i+1], 12)
    slow = ema(closes[:i+1], 26)
    macd_vals.append(fast - slow)

if len(macd_vals) < 9:
    return None

signal = ema(macd_vals, 9)
return macd_vals[-1] - signal
```

def atr(candles, period=14):
if len(candles) < period + 1:
return None

```
trs = []
for i in range(1, len(candles)):
    high = candles[i]["high"]
    low = candles[i]["low"]
    prev_close = candles[i-1]["close"]

    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    trs.append(tr)

return sum(trs[-period:]) / period
```

# ================= ANALYSIS =================

def analyze(coin):
candles = get_klines(coin)
if not candles or len(candles) < 50:
return None

```
closes = [c["close"] for c in candles]
price = closes[-1]

rsi_val = rsi(closes)
macd_val = macd_hist(closes)
ema20 = ema(closes, 20)
ema50 = ema(closes, 50)
atr_val = atr(candles)

if not all([rsi_val, ema20, ema50, atr_val]):
    return None

bull, bear = 0, 0

# RSI
if rsi_val < 30:
    bull += 30
elif rsi_val < 40:
    bull += 15
elif rsi_val > 70:
    bear += 30
elif rsi_val > 60:
    bear += 15

# MACD
if macd_val:
    if macd_val > 0:
        bull += 25
    else:
        bear += 25

# EMA trend
if ema20 > ema50 and price > ema20:
    bull += 25
elif ema20 < ema50 and price < ema20:
    bear += 25

# Volume
recent_vol = sum(c["volume"] for c in candles[-5:]) / 5
avg_vol = sum(c["volume"] for c in candles[-20:]) / 20

if recent_vol > avg_vol * 1.3:
    if bull > bear:
        bull += 10
    else:
        bear += 10

# Decision
if bull >= MIN_CONFIDENCE and bull > bear:
    direction, confidence = "LONG", min(bull, 95)
elif bear >= MIN_CONFIDENCE and bear > bull:
    direction, confidence = "SHORT", min(bear, 95)
else:
    return None

decimals = 2 if price > 100 else (4 if price > 1 else 6)

if direction == "LONG":
    sl = price - (atr_val * 1.5)
    tp1 = price + (atr_val * 2)
    tp2 = price + (atr_val * 3.5)
else:
    sl = price + (atr_val * 1.5)
    tp1 = price - (atr_val * 2)
    tp2 = price - (atr_val * 3.5)

risk = abs(price - sl)
rr = round(abs(tp1 - price) / risk, 1) if risk > 0 else 1.5

return {
    "coin": coin,
    "direction": direction,
    "confidence": int(confidence),
    "entry_low": round(price * 0.998, decimals),
    "entry_high": round(price * 1.002, decimals),
    "sl": round(sl, decimals),
    "tp1": round(tp1, decimals),
    "tp2": round(tp2, decimals),
    "rr": f"1:{rr}",
    "risk": "AUTO",
    "valid_mins": 60,
    "status": "ACTIVE",
    "source": "ai_bot"
}
```

# ================= DATABASE =================

def post_signal(signal):
try:
url = f"{SUPABASE_URL}/rest/v1/bot_signals"
r = requests.post(url, headers=HEADERS, json=signal, timeout=10)

```
    print(f"POST {signal['coin']} -> {r.status_code}")

    if r.status_code not in (200, 201, 204):
        print("Error:", r.text)

    return r.status_code in (200, 201, 204)

except Exception as e:
    print("Post error:", e)
    return False
```

def get_active():
try:
url = f"{SUPABASE_URL}/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin&order=created_at.desc"
r = requests.get(url, headers=HEADERS, timeout=10)

```
    if r.status_code == 200:
        return r.json()

    print("Fetch error:", r.text)
    return []

except Exception as e:
    print("Fetch error:", e)
    return []
```

# ================= MAIN =================

active = get_active()
active_coins = [s["coin"] for s in active]

print("Active signals:", len(active))

new_signals = []

for coin in COINS:
if coin in active_coins:
print("Skip:", coin)
continue

```
print("Scan:", coin)
signal = analyze(coin)

time.sleep(0.2)

if signal:
    print(" ->", signal["direction"], signal["confidence"], "%")
    new_signals.append(signal)
```

print("Signals found:", len(new_signals))

for sig in new_signals:
post_signal(sig)

# limit active signals

if len(active) + len(new_signals) > MAX_ACTIVE:
all_active = get_active()

```
for old in all_active[MAX_ACTIVE:]:
    try:
        url = f"{SUPABASE_URL}/rest/v1/bot_signals?id=eq.{old['id']}"
        requests.patch(url, headers=HEADERS, json={"status": "CLOSED"}, timeout=10)
        print("Closed:", old["coin"])
    except Exception as e:
        print("Close error:", e)
```

print("Done!")
