import requests
import datetime
import os
import time
import logging

logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("TradexoBot")

CONFIG = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
    "SUPABASE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),

    # ❌ INJ removed
    "COINS": ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","LTC","LINK","ATOM","NEAR","TRX","AAVE","OP","ARB","SUI","APT"],

    "MIN_SCORE": 3.5,
    "MAX_ACTIVE": 10,
    "MIN_ADX": 18,
    "MIN_ATR_PCT": 0.3,

    # ✅ CONFIDENCE CONTROL ADDED
    "CONFIDENCE_MODE": 70,

    "CAPITAL": 1000.0,
    "RISK_PCT": 0.01,

    "ATR_SL_MULT_STRONG": 1.2,
    "ATR_SL_MULT_WEAK": 1.5,
    "ATR_TP1_MULT_STRONG": 2.2,
    "ATR_TP1_MULT_WEAK": 1.8,
    "ATR_TP2_MULT_STRONG": 4.5,
    "ATR_TP2_MULT_WEAK": 3.5,

    "VALID_MINS": 240,
    "SLEEP": 0.5,
    "BINANCE_URL": "https://api.binance.us/api/v3/klines",

    "TELEGRAM_TOKEN": "YOUR_BOT_TOKEN",

    "TELEGRAM_CHANNELS": {
        "free":    "-1003543150372",
        "starter": "-1003871305269",
        "pro":     "-1003832374485",
        "vip":     "-1003741068762",
    },
}

SUPA = CONFIG["SUPABASE_URL"]
KEY  = CONFIG["SUPABASE_KEY"]

HD = {
    "apikey": KEY,
    "Authorization": "Bearer " + KEY,
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

_tg_cache = set()
expired_coins = set()   # ✅ FIX: no duplicate expiry spam
sent_coins = set()      # ✅ FIX: repeat signal block

# ---------------- TELEGRAM ----------------
def send_telegram(chat_id, text, cache_key=None):
    global _tg_cache
    if cache_key:
        k = str(chat_id)+":"+cache_key
        if k in _tg_cache:
            return
        _tg_cache.add(k)

    if len(text) > 4000:
        text = text[:3997]+"..."

    try:
        requests.post(
            "https://api.telegram.org/bot"+CONFIG["TELEGRAM_TOKEN"]+"/sendMessage",
            json={"chat_id":chat_id,"text":text,"parse_mode":"HTML"},
            timeout=10
        )
    except:
        pass

# ---------------- CONFIDENCE FILTER ----------------
def confidence_allowed(conf):
    mode = CONFIG["CONFIDENCE_MODE"]
    if mode == 60:
        return conf >= 50
    if mode == 70:
        return conf >= 60
    if mode == 80:
        return conf >= 70
    return True

# ---------------- SIGNAL BUILD ----------------
def build_signal_message(sig):
    return (
        f"📊 <b>{sig['coin']} SIGNAL</b>\n"
        f"Direction: {sig['direction']}\n"
        f"Confidence: {sig['confidence']}%\n"
        f"Entry: {sig['entry_price']}\n"
        f"SL: {sig['sl']}\n"
        f"TP1: {sig['tp1']}\n"
        f"TP2: {sig['tp2']}\n"
    )

# ---------------- EXPIRY FIX ----------------
def expire_old_signals():
    global expired_coins
    try:
        r = requests.get(SUPA+"/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin,created_at,valid_mins",headers=HD)
        if r.status_code != 200:
            return

        now = datetime.datetime.utcnow()

        for s in r.json():
            coin = s["coin"]
            if coin in expired_coins:
                continue

            created = datetime.datetime.strptime(s["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
            age = (now-created).total_seconds()/60

            if age > (s.get("valid_mins") or 120):
                expired_coins.add(coin)

                requests.patch(
                    SUPA+"/rest/v1/bot_signals?id=eq."+str(s["id"]),
                    headers=HD,
                    json={"status":"CLOSED"}
                )

    except Exception as e:
        log.error(e)

# ✅ BATCH EXPIRY MESSAGE (ONLY ONCE)
def send_expiry_summary():
    global expired_coins
    if not expired_coins:
        return

    msg = "⏱ <b>SIGNALS EXPIRED</b>\n\n"
    msg += ", ".join(list(expired_coins))

    for ch in CONFIG["TELEGRAM_CHANNELS"].values():
        send_telegram(ch, msg)

    expired_coins.clear()

# ---------------- MAIN ANALYSIS FILTER ----------------
def analyze_coin(coin):
    if coin in sent_coins:
        return None

    # dummy signal (replace with your full logic)
    conf = 72

    if not confidence_allowed(conf):
        return None

    sig = {
        "coin": coin,
        "direction": "LONG",
        "confidence": conf,
        "entry_price": 100,
        "sl": 95,
        "tp1": 110,
        "tp2": 120
    }

    sent_coins.add(coin)
    return sig

# ---------------- MAIN ----------------
def main():
    log.info("Bot started")

    expire_old_signals()
    send_expiry_summary()

    for coin in CONFIG["COINS"]:
        sig = analyze_coin(coin)
        if sig:
            msg = build_signal_message(sig)
            send_telegram(CONFIG["TELEGRAM_CHANNELS"]["vip"], msg)

    log.info("Done")

main()
