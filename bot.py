import os
import time
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

COINS = [
    "BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE",
    "DOT","MATIC","LINK","LTC","NEAR","TRX","TON","ATOM"
]

MIN_CONFIDENCE = 20  # 🔥 TEST MODE


# ================= BINANCE =================

def get_klines(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": f"{symbol}USDT",
        "interval": "15m",
        "limit": 100
    }

    r = requests.get(url, params=params)
    print("Binance:", symbol, r.status_code)

    if r.status_code != 200:
        return None

    return [
        {
            "close": float(c[4]),
            "high": float(c[2]),
            "low": float(c[3]),
            "volume": float(c[5]),
        }
        for c in r.json()
    ]


# ================= INDICATORS =================

def ema(values, period):
    if len(values) < period:
        return None

    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period

    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    gains, losses = 0, 0

    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff

    if losses == 0:
        return 100

    rs = gains / losses
    return 100 - (100 / (1 + rs))


def macd(closes):
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)

    if not e12 or not e26:
        return None

    return e12 - e26


# ================= SIGNAL =================

def analyze(coin):
    data = get_klines(coin)
    if not data:
        return None

    closes = [c["close"] for c in data]

    r = rsi(closes)
    m = macd(closes)
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)

    if not all([r, m, e20, e50]):
        return None

    bull = 0
    bear = 0

    if r < 30:
        bull += 30
    elif r > 70:
        bear += 30

    if m > 0:
        bull += 20
    else:
        bear += 20

    if e20 > e50:
        bull += 20
    else:
        bear += 20

    if bull > bear and bull >= MIN_CONFIDENCE:
        return {
            "coin": coin,
            "direction": "LONG",
            "confidence": bull,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    if bear > bull and bear >= MIN_CONFIDENCE:
        return {
            "coin": coin,
            "direction": "SHORT",
            "confidence": bear,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    return None


# ================= SUPABASE =================

def post_signal(signal):
    url = f"{SUPABASE_URL}/rest/v1/bot_signals"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=signal)

    print("POST:", signal["coin"], signal["direction"], "→", r.status_code)
    print("RESPONSE:", r.text)


# ================= MAIN =================

def main():
    print("🚀 Bot started at", datetime.now(timezone.utc))

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Missing Supabase credentials")

    # 🔥 FORCE TEST SIGNAL (guaranteed insert)
    test_signal = {
        "coin": "BTC",
        "direction": "LONG",
        "confidence": 99,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    print("Sending test signal...")
    post_signal(test_signal)

    # 🔄 REAL SCAN
    for coin in COINS:
        print("Scanning:", coin)

        signal = analyze(coin)
        time.sleep(0.3)

        if signal:
            print("Signal found:", signal)
            post_signal(signal)

    print("✅ Done")


if __name__ == "__main__":
    main()