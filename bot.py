“””
TradexoAI Signal Generator Bot
Generates crypto trading signals using technical analysis
Posts to Supabase bot_signals table
“””

import os
import json
import time
import requests
from datetime import datetime, timezone

# ============== CONFIG ==============

SUPABASE_URL = os.environ.get(‘SUPABASE_URL’, ‘https://maftyyqruhbaiiafivmh.supabase.co’)
SUPABASE_KEY = os.environ.get(‘SUPABASE_SERVICE_KEY’, ‘’)

# Top coins to scan (Binance symbols)

COINS = [
‘BTC’, ‘ETH’, ‘BNB’, ‘SOL’, ‘XRP’, ‘ADA’, ‘AVAX’, ‘DOGE’,
‘DOT’, ‘MATIC’, ‘LINK’, ‘LTC’, ‘NEAR’, ‘TRX’, ‘TON’, ‘ATOM’
]

# Min confidence to post signal (0-100)

MIN_CONFIDENCE = 65

# How many signals to keep ACTIVE (close older ones beyond this)

MAX_ACTIVE_SIGNALS = 8

# ============== BINANCE API ==============

def get_klines(symbol, interval=‘15m’, limit=100):
“”“Fetch candlestick data from Binance (no API key needed)”””
try:
url = f’https://api.binance.com/api/v3/klines’
params = {‘symbol’: f’{symbol}USDT’, ‘interval’: interval, ‘limit’: limit}
r = requests.get(url, params=params, timeout=10)
if r.status_code != 200:
return None
data = r.json()
# [open_time, open, high, low, close, volume, …]
return [{
‘open’: float(c[1]), ‘high’: float(c[2]),
‘low’: float(c[3]), ‘close’: float(c[4]),
‘volume’: float(c[5]), ‘time’: c[0]
} for c in data]
except Exception as e:
print(f”  Error fetching {symbol}: {e}”)
return None

# ============== INDICATORS ==============

def sma(values, period):
“”“Simple Moving Average”””
if len(values) < period:
return None
return sum(values[-period:]) / period

def ema(values, period):
“”“Exponential Moving Average”””
if len(values) < period:
return None
multiplier = 2 / (period + 1)
ema_val = sum(values[:period]) / period
for v in values[period:]:
ema_val = (v - ema_val) * multiplier + ema_val
return ema_val

def rsi(closes, period=14):
“”“Relative Strength Index”””
if len(closes) < period + 1:
return None
gains, losses = [], []
for i in range(1, len(closes)):
change = closes[i] - closes[i-1]
gains.append(max(change, 0))
losses.append(abs(min(change, 0)))
avg_gain = sum(gains[-period:]) / period
avg_loss = sum(losses[-period:]) / period
if avg_loss == 0:
return 100
rs = avg_gain / avg_loss
return 100 - (100 / (1 + rs))

def macd(closes, fast=12, slow=26, signal=9):
“”“MACD indicator”””
if len(closes) < slow + signal:
return None, None, None
ema_fast = ema(closes, fast)
ema_slow = ema(closes, slow)
macd_line = ema_fast - ema_slow
# Signal line = EMA of MACD
macd_values = []
for i in range(slow, len(closes)):
ef = ema(closes[:i+1], fast)
es = ema(closes[:i+1], slow)
macd_values.append(ef - es)
if len(macd_values) < signal:
return macd_line, None, None
sig_line = ema(macd_values, signal)
histogram = macd_line - sig_line
return macd_line, sig_line, histogram

def atr(candles, period=14):
“”“Average True Range (volatility)”””
if len(candles) < period + 1:
return None
trs = []
for i in range(1, len(candles)):
h = candles[i][‘high’]
l = candles[i][‘low’]
pc = candles[i-1][‘close’]
tr = max(h - l, abs(h - pc), abs(l - pc))
trs.append(tr)
return sum(trs[-period:]) / period

def bollinger_bands(closes, period=20, std_dev=2):
“”“Bollinger Bands”””
if len(closes) < period:
return None, None, None
middle = sma(closes, period)
recent = closes[-period:]
variance = sum((x - middle) ** 2 for x in recent) / period
std = variance ** 0.5
upper = middle + (std_dev * std)
lower = middle - (std_dev * std)
return upper, middle, lower

# ============== SIGNAL GENERATION ==============

def analyze_coin(coin):
“”“Analyze coin and generate signal if conditions match”””
candles = get_klines(coin, ‘15m’, 100)
if not candles or len(candles) < 50:
return None

```
closes = [c['close'] for c in candles]
current_price = closes[-1]

# Calculate indicators
rsi_val = rsi(closes)
macd_line, signal_line, histogram = macd(closes)
ema_20 = ema(closes, 20)
ema_50 = ema(closes, 50)
atr_val = atr(candles)
bb_upper, bb_middle, bb_lower = bollinger_bands(closes)

if not all([rsi_val, macd_line, ema_20, ema_50, atr_val, bb_upper]):
    return None

# Count bullish/bearish signals
bull_score = 0
bear_score = 0

# RSI signals
if rsi_val < 30:
    bull_score += 25  # Oversold
elif rsi_val < 40:
    bull_score += 10
elif rsi_val > 70:
    bear_score += 25  # Overbought
elif rsi_val > 60:
    bear_score += 10

# MACD signals
if histogram and histogram > 0 and macd_line > signal_line:
    bull_score += 20
elif histogram and histogram < 0 and macd_line < signal_line:
    bear_score += 20

# EMA trend
if ema_20 > ema_50 and current_price > ema_20:
    bull_score += 20  # Uptrend
elif ema_20 < ema_50 and current_price < ema_20:
    bear_score += 20  # Downtrend

# Bollinger Bands
if current_price <= bb_lower:
    bull_score += 15  # Price at lower band
elif current_price >= bb_upper:
    bear_score += 15  # Price at upper band

# Volume confirmation
recent_vol = sum(c['volume'] for c in candles[-5:]) / 5
avg_vol = sum(c['volume'] for c in candles[-20:]) / 20
if recent_vol > avg_vol * 1.3:
    if bull_score > bear_score:
        bull_score += 10
    else:
        bear_score += 10

# Determine direction and confidence
if bull_score >= MIN_CONFIDENCE and bull_score > bear_score:
    direction = 'LONG'
    confidence = min(bull_score, 95)
elif bear_score >= MIN_CONFIDENCE and bear_score > bull_score:
    direction = 'SHORT'
    confidence = min(bear_score, 95)
else:
    return None  # No clear signal

# Calculate Entry, SL, TP using ATR
if direction == 'LONG':
    entry_low = current_price * 0.998
    entry_high = current_price * 1.002
    sl = current_price - (atr_val * 1.5)
    tp1 = current_price + (atr_val * 2)
    tp2 = current_price + (atr_val * 3.5)
else:
    entry_low = current_price * 0.998
    entry_high = current_price * 1.002
    sl = current_price + (atr_val * 1.5)
    tp1 = current_price - (atr_val * 2)
    tp2 = current_price - (atr_val * 3.5)

# Risk/Reward
risk = abs(current_price - sl)
reward = abs(tp1 - current_price)
rr = round(reward / risk, 1) if risk > 0 else 1.5

# Risk level based on ATR%
atr_percent = (atr_val / current_price) * 100
if atr_percent < 1.5:
    risk_label = 'LOW RISK'
elif atr_percent < 3:
    risk_label = 'MEDIUM RISK'
else:
    risk_label = 'HIGH RISK'

# Round prices
decimals = 2 if current_price > 100 else (4 if current_price > 1 else 6)

return {
    'coin': coin,
    'direction': direction,
    'confidence': int(confidence),
    'entry_low': round(entry_low, decimals),
    'entry_high': round(entry_high, decimals),
    'sl': round(sl, decimals),
    'tp1': round(tp1, decimals),
    'tp2': round(tp2, decimals),
    'rr': f'1:{rr}',
    'risk': risk_label,
    'valid_mins': 60,
    'status': 'ACTIVE',
    'source': 'ai_bot'
}
```

# ============== SUPABASE ==============

def post_signal(signal):
“”“Post signal to Supabase”””
try:
url = f’{SUPABASE_URL}/rest/v1/bot_signals’
headers = {
‘apikey’: SUPABASE_KEY,
‘Authorization’: f’Bearer {SUPABASE_KEY}’,
‘Content-Type’: ‘application/json’,
‘Prefer’: ‘return=minimal’
}
r = requests.post(url, headers=headers, json=signal, timeout=10)
return r.status_code in (200, 201, 204)
except Exception as e:
print(f”  Post error: {e}”)
return False

def get_active_signals():
“”“Get current active signals from Supabase”””
try:
url = f’{SUPABASE_URL}/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin,created_at&order=created_at.desc’
headers = {‘apikey’: SUPABASE_KEY, ‘Authorization’: f’Bearer {SUPABASE_KEY}’}
r = requests.get(url, headers=headers, timeout=10)
if r.status_code == 200:
return r.json()
return []
except:
return []

def close_old_signals(active_signals):
“”“Close oldest signals if more than MAX_ACTIVE_SIGNALS”””
if len(active_signals) <= MAX_ACTIVE_SIGNALS:
return

```
to_close = active_signals[MAX_ACTIVE_SIGNALS:]
for sig in to_close:
    try:
        url = f'{SUPABASE_URL}/rest/v1/bot_signals?id=eq.{sig["id"]}'
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        requests.patch(url, headers=headers, json={'status': 'CLOSED'}, timeout=10)
        print(f"  Closed old signal: {sig['coin']}")
    except:
        pass
```

# ============== MAIN ==============

def main():
print(f”\n{’=’*50}”)
print(f”TradexoAI Signal Bot — {datetime.now(timezone.utc).isoformat()}”)
print(f”{’=’*50}”)

```
if not SUPABASE_KEY:
    print("ERROR: SUPABASE_SERVICE_KEY env var missing!")
    return

# Get active signals
active = get_active_signals()
active_coins = [s['coin'] for s in active]
print(f"Active signals: {len(active)} ({', '.join(active_coins) if active_coins else 'none'})")

# Scan coins
new_signals = []
for coin in COINS:
    if coin in active_coins:
        print(f"  {coin}: skip (already active)")
        continue
    
    print(f"  {coin}: scanning...", end='')
    signal = analyze_coin(coin)
    time.sleep(0.3)  # Rate limit
    
    if signal:
        print(f" ✓ {signal['direction']} {signal['confidence']}%")
        new_signals.append(signal)
    else:
        print(" no signal")

# Post new signals
print(f"\nNew signals: {len(new_signals)}")
for sig in new_signals:
    if post_signal(sig):
        print(f"  ✓ Posted {sig['coin']} {sig['direction']} ({sig['confidence']}%)")
    else:
        print(f"  ✗ Failed {sig['coin']}")

# Cleanup old signals
if new_signals:
    active = get_active_signals()
    close_old_signals(active)

print(f"\nDone. Total active: {len(get_active_signals())}")
```

if **name** == ‘**main**’:
main()