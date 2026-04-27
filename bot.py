import os
import json
import time
import requests
from datetime import datetime, timezone

# CONFIG

SUPABASE_URL = os.environ[‘SUPABASE_URL’]
SUPABASE_KEY = os.environ[‘SUPABASE_SERVICE_KEY’]

COINS = [
‘BTC’, ‘ETH’, ‘BNB’, ‘SOL’, ‘XRP’, ‘ADA’, ‘AVAX’, ‘DOGE’,
‘DOT’, ‘MATIC’, ‘LINK’, ‘LTC’, ‘NEAR’, ‘TRX’, ‘TON’, ‘ATOM’
]

MIN_CONFIDENCE = 45
MAX_ACTIVE_SIGNALS = 8

HEADERS = {
‘apikey’: SUPABASE_KEY,
‘Authorization’: f’Bearer {SUPABASE_KEY}’,
‘Content-Type’: ‘application/json’,
‘Prefer’: ‘return=minimal’
}

print(f”Bot started at {datetime.now()}”)
print(f”SUPABASE_URL: {SUPABASE_URL}”)
print(f”KEY present: {‘YES’ if SUPABASE_KEY else ‘NO’}”)
print(f”KEY first 20 chars: {SUPABASE_KEY[:20]}…”)

def get_klines(symbol, interval=‘15m’, limit=100):
try:
url = ‘https://api.binance.com/api/v3/klines’
params = {‘symbol’: f’{symbol}USDT’, ‘interval’: interval, ‘limit’: limit}
r = requests.get(url, params=params, timeout=10)
if r.status_code != 200:
return None
data = r.json()
return [{
‘open’: float(c[1]), ‘high’: float(c[2]),
‘low’: float(c[3]), ‘close’: float(c[4]),
‘volume’: float(c[5])
} for c in data]
except Exception as e:
print(f”  Binance error {symbol}: {e}”)
return None

def ema(values, period):
if len(values) < period:
return None
m = 2 / (period + 1)
v = sum(values[:period]) / period
for x in values[period:]:
v = (x - v) * m + v
return v

def rsi(closes, period=14):
if len(closes) < period + 1:
return None
gains, losses = [], []
for i in range(1, len(closes)):
d = closes[i] - closes[i-1]
gains.append(max(d, 0))
losses.append(abs(min(d, 0)))
ag = sum(gains[-period:]) / period
al = sum(losses[-period:]) / period
if al == 0:
return 100
return 100 - (100 / (1 + ag/al))

def macd(closes):
if len(closes) < 35:
return None, None, None
e12 = ema(closes, 12)
e26 = ema(closes, 26)
ml = e12 - e26
mv = []
for i in range(26, len(closes)):
ef = ema(closes[:i+1], 12)
es = ema(closes[:i+1], 26)
mv.append(ef - es)
if len(mv) < 9:
return ml, None, None
sl = ema(mv, 9)
return ml, sl, ml - sl

def atr(candles, period=14):
if len(candles) < period + 1:
return None
trs = []
for i in range(1, len(candles)):
h, l, pc = candles[i][‘high’], candles[i][‘low’], candles[i-1][‘close’]
trs.append(max(h-l, abs(h-pc), abs(l-pc)))
return sum(trs[-period:]) / period

def analyze(coin):
candles = get_klines(coin)
if not candles or len(candles) < 50:
return None

```
closes = [c['close'] for c in candles]
price = closes[-1]

rsi_v = rsi(closes)
ml, sl, hist = macd(closes)
e20 = ema(closes, 20)
e50 = ema(closes, 50)
atr_v = atr(candles)

if not all([rsi_v, e20, e50, atr_v]):
    return None

bull = 0
bear = 0

if rsi_v < 30: bull += 30
elif rsi_v < 40: bull += 15
elif rsi_v > 70: bear += 30
elif rsi_v > 60: bear += 15

if hist:
    if hist > 0: bull += 25
    else: bear += 25

if e20 > e50 and price > e20: bull += 25
elif e20 < e50 and price < e20: bear += 25

rv = sum(c['volume'] for c in candles[-5:]) / 5
av = sum(c['volume'] for c in candles[-20:]) / 20
if rv > av * 1.3:
    if bull > bear: bull += 10
    else: bear += 10

if bull >= MIN_CONFIDENCE and bull > bear:
    direction, conf = 'LONG', min(bull, 95)
elif bear >= MIN_CONFIDENCE and bear > bull:
    direction, conf = 'SHORT', min(bear, 95)
else:
    return None

dec = 2 if price > 100 else (4 if price > 1 else 6)

if direction == 'LONG':
    sl_price = price - (atr_v * 1.5)
    tp1 = price + (atr_v * 2)
    tp2 = price + (atr_v * 3.5)
else:
    sl_price = price + (atr_v * 1.5)
    tp1 = price - (atr_v * 2)
    tp2 = price - (atr_v * 3.5)

risk = abs(price - sl_price)
rr = round(abs(tp1 - price) / risk, 1) if risk > 0 else 1.5
atr_pct = (atr_v / price) * 100
risk_lbl = 'LOW RISK' if atr_pct < 1.5 else ('MEDIUM RISK' if atr_pct < 3 else 'HIGH RISK')

return {
    'coin': coin,
    'direction': direction,
    'confidence': int(conf),
    'entry_low': round(price * 0.998, dec),
    'entry_high': round(price * 1.002, dec),
    'sl': round(sl_price, dec),
    'tp1': round(tp1, dec),
    'tp2': round(tp2, dec),
    'rr': f'1:{rr}',
    'risk': risk_lbl,
    'valid_mins': 60,
    'status': 'ACTIVE',
    'source': 'ai_bot'
}
```

def post_signal(sig):
r = requests.post(
f’{SUPABASE_URL}/rest/v1/bot_signals’,
headers=HEADERS,
json=sig,
timeout=10
)
print(f”  POST {sig[‘coin’]} {sig[‘direction’]} → {r.status_code}”)
if r.status_code not in (200, 201, 204):
print(f”  ERROR: {r.text}”)
return r.status_code in (200, 201, 204)

def get_active():
r = requests.get(
f’{SUPABASE_URL}/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin&order=created_at.desc’,
headers=HEADERS,
timeout=10
)
return r.json() if r.status_code == 200 else []

def main():
active = get_active()
active_coins = [s[‘coin’] for s in active]
print(f”Active signals: {len(active)}”)

```
new_sigs = []
for coin in COINS:
    if coin in active_coins:
        continue
    print(f"Scanning: {coin}")
    sig = analyze(coin)
    time.sleep(0.2)
    if sig:
        print(f"  Signal: {sig['direction']} {sig['confidence']}%")
        new_sigs.append(sig)

print(f"\nPosting {len(new_sigs)} signals...")
for sig in new_sigs:
    post_signal(sig)

# Close oldest if too many
if len(active) + len(new_sigs) > MAX_ACTIVE_SIGNALS:
    all_active = get_active()
    for old in all_active[MAX_ACTIVE_SIGNALS:]:
        requests.patch(
            f'{SUPABASE_URL}/rest/v1/bot_signals?id=eq.{old["id"]}',
            headers=HEADERS,
            json={'status': 'CLOSED'},
            timeout=10
        )

print(f"Done!")
```

main()