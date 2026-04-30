import requests
import datetime
import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("TradexoBot")

CONFIG = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
    "SUPABASE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),

    "COINS": ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","LTC",
              "LINK","ATOM","NEAR","TRX","AAVE","OP","ARB","INJ","SUI","APT"],

    "MIN_SCORE": 3.5,
    "MAX_ACTIVE": 10,

    # ✅ CONFIDENCE CONTROL (CHANGE HERE)
    # 60 = normal, 70 = safer, 80 = very strict
    "CONFIDENCE_THRESHOLD": 60,

    "MIN_ADX": 18,
    "MIN_ATR_PCT": 0.3,

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

    "TELEGRAM_TOKEN": "YOUR_TOKEN_HERE",
    "TELEGRAM_CHANNELS": {
        "free": "-1003543150372",
        "starter": "-1003871305269",
        "pro": "-1003832374485",
        "vip": "-1003741068762",
    },
}

SUPA = CONFIG["SUPABASE_URL"]
KEY = CONFIG["SUPABASE_KEY"]

HD = {
    "apikey": KEY,
    "Authorization": "Bearer " + KEY,
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

_tg_cache = set()


def send_telegram(chat_id, text, cache_key=None):
    global _tg_cache
    if cache_key:
        k = str(chat_id) + ":" + cache_key
        if k in _tg_cache:
            return
        _tg_cache.add(k)

    if len(text) > 4000:
        text = text[:3997] + "..."

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.telegram.org/bot" + CONFIG["TELEGRAM_TOKEN"] + "/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10
            )
            if r.status_code == 200:
                return
        except:
            pass
        time.sleep(1)


# ---------------- SIGNAL MESSAGE ----------------
def build_signal_message(sig, status_type="new"):
    coin = sig["coin"]
    direction = sig["direction"]
    emoji = "🟢" if direction == "LONG" else "🔴"
    arrow = "📈" if direction == "LONG" else "📉"

    if status_type == "new":
        return (
            f"{arrow} <b>NEW SIGNAL — {coin}/USDT</b>\n\n"
            f"{emoji} <b>Direction:</b> {direction}\n"
            f"🎯 <b>Confidence:</b> {sig['confidence']}%\n"
            f"💰 <b>Entry:</b> ${sig['entry_low']} - ${sig['entry_high']}\n"
            f"🛑 <b>SL:</b> ${sig['sl']}\n"
            f"✅ <b>TP1:</b> ${sig['tp1']}\n"
            f"🏆 <b>TP2:</b> ${sig['tp2']}\n"
            f"⚖️ <b>RR:</b> {sig['rr']}\n"
            f"⏱ <b>Valid:</b> {sig['valid_mins']} mins"
        )


# ---------------- CONFIDENCE FILTER ----------------
def pass_confidence(sig):
    return sig["confidence"] >= CONFIG["CONFIDENCE_THRESHOLD"]


# ---------------- EXPIRY FIX (COLLECTIVE) ----------------
expired_coins = []


def expire_old_signals():
    global expired_coins
    expired_coins = []

    try:
        r = requests.get(
            SUPA + "/rest/v1/bot_signals?status=eq.ACTIVE&select=*",
            headers=HD,
            timeout=10
        )

        if r.status_code != 200:
            return

        now = datetime.datetime.utcnow()

        for sig in r.json():
            cs = sig.get("created_at")
            vm = sig.get("valid_mins") or 120
            if not cs:
                continue

            created = datetime.datetime.strptime(cs[:19], "%Y-%m-%dT%H:%M:%S")
            age = (now - created).total_seconds() / 60

            if age > vm:
                coin = sig["coin"]

                requests.patch(
                    SUPA + "/rest/v1/bot_signals?id=eq." + str(sig["id"]),
                    headers=HD,
                    json={"status": "CLOSED"}
                )

                expired_coins.append(coin)

        # ✅ SINGLE TELEGRAM MESSAGE
        if expired_coins:
            msg = "⏱ <b>SIGNALS EXPIRED</b>\n\n"
            msg += ", ".join(expired_coins)

            for ch in CONFIG["TELEGRAM_CHANNELS"].values():
                send_telegram(ch, msg)

    except Exception as e:
        log.error("expiry error: %s", e)


# ---------------- MAIN ANALYSIS HOOK ----------------
def analyze(coin):
    # (your original logic stays SAME)
    # IMPORTANT ADD ONLY ONE LINE BEFORE RETURN:

    sig = None  # placeholder for your real logic

    if sig:
        if not pass_confidence(sig):
            log.info("%s skipped due to confidence", coin)
            return None

    return sig


# ---------------- MAIN ----------------
def main():
    log.info("Bot started")

    expire_old_signals()

    log.info("Done")


main()
