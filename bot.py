import requests
import datetime
import os

# 🔐 ENV (GitHub Secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 📡 Headers
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# 📤 Send data
def post_signal(signal):
    url = f"{SUPABASE_URL}/rest/v1/bot_signals"

    print("FINAL SIGNAL:", signal)  # ✅ DEBUG

    r = requests.post(url, headers=headers, json=signal)

    print(f"POST: {signal['symbol']} {signal['direction']} → {signal['entry_price']}")
    print("RESPONSE:", r.text)


# 🧠 Create signal (FIXED)
def create_signal(symbol, direction, price):
    action = "BUY" if direction == "LONG" else "SELL"

    signal = {
        "symbol": symbol,          # ✅ required
        "action": action,          # ✅ FIX (IMPORTANT)
        "direction": direction,
        "entry_price": price,
        "exchange": "binance",
        "market_type": "FUTURES",
        "leverage": 5,
        "status": "ACTIVE",
        "source": "tradingview",
        "risk": "MEDIUM RISK",
        "timeframe": 60,
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    return signal


# 🚀 Main
def main():
    print("🚀 Bot started at", datetime.datetime.utcnow())

    # 🔥 TEST SIGNAL
    print("Sending test signal...")
    test_signal = create_signal("BTC", "LONG", 400)
    post_signal(test_signal)

    # 🔍 Scan coins
    coins = [
        "BTC","ETH","BNB","SOL","XRP","ADA",
        "AVAX","DOGE","DOT","MATIC","LINK",
        "LTC","NEAR","TRX","TON","ATOM"
    ]

    for coin in coins:
        print(f"Scanning: {coin}")

        price = 451  # dummy

        print(f"Binance: {coin} {price}")

        if coin == "BTC":
            signal = create_signal(coin, "LONG", price)
            post_signal(signal)

    print("✅ Done")


if __name__ == "__main__":
    main()