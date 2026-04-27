import os
import time
import requests
from datetime import datetime, timezone

print("🔥 VERSION FINAL V3 RUNNING")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

COINS = ["BTC", "ETH", "BNB", "SOL"]


def post_signal(signal):
    url = f"{SUPABASE_URL}/rest/v1/bot_signals"

    headers = {
        "apikey": SUPABASE_KEY.strip(),
        "Authorization": f"Bearer {SUPABASE_KEY.strip()}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=signal)

    print("POST:", signal["symbol"], signal["direction"], "→", r.status_code)
    print("RESPONSE:", r.text)


def build_signal(coin, direction):
    return {
        "coin": coin,
        "symbol": f"{coin}USDT",
        "direction": direction,
        "action": "BUY" if direction == "LONG" else "SELL",
        "confidence": 90,
        "status": "ACTIVE",
        "exchange": "binance",
        "market_type": "FUTURES",
        "leverage": 5,
        "source": "tradingview",
        "risk": "MEDIUM RISK",
        "timeframe": 60,
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    print("🚀 Bot started at", datetime.now(timezone.utc))

    # 🔥 TEST SIGNAL (guaranteed insert)
    test_signal = build_signal("BTC", "LONG")
    print("Sending test signal...")
    post_signal(test_signal)

    # 🔄 LOOP
    for coin in COINS:
        print("Scanning:", coin)

        signal = build_signal(coin, "LONG")
        post_signal(signal)

        time.sleep(1)

    print("✅ Done")


if __name__ == "__main__":
    main()