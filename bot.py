import os
import time
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

COINS = ["BTC","ETH","BNB","SOL"]

MIN_CONFIDENCE = 20


def post_signal(signal):
    url = f"{SUPABASE_URL}/rest/v1/bot_signals"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=signal)

    print("POST:", signal["symbol"], signal["direction"], "→", r.status_code)
    print("Response:", r.text)


def main():
    print("🚀 Bot started at", datetime.now(timezone.utc))

    # 🔥 TEST SIGNAL (guaranteed insert)
    test_signal = {
        "coin": "BTC",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 99,
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    post_signal(test_signal)

    # 🔄 Simple scan (demo)
    for coin in COINS:
        print("Scanning:", coin)

        signal = {
            "coin": coin,
            "symbol": f"{coin}USDT",
            "direction": "LONG",
            "confidence": 50,
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        post_signal(signal)
        time.sleep(1)

    print("✅ Done")


if __name__ == "__main__":
    main()