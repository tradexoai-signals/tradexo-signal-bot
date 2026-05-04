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
    "COINS": ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","LTC","LINK","ATOM","NEAR","TRX","AAVE","OP","ARB","SUI","APT"],
    "MIN_SCORE": 6.2,
    "MAX_ACTIVE": 10,
    "MIN_ADX": 25,
    "MIN_ATR_PCT": 0.2,
    "CAPITAL": 1000.0,
    "RISK_PCT": 0.01,
    "ATR_SL_MULT_STRONG": 2.0,
    "ATR_SL_MULT_WEAK": 2.5,
    "ATR_TP1_MULT_STRONG": 2.0,
    "ATR_TP1_MULT_WEAK": 1.8,
    "ATR_TP2_MULT_STRONG": 4.5,
    "ATR_TP2_MULT_WEAK": 3.5,
    "VALID_MINS": 360,
    "SLEEP": 0.5,
    "BINANCE_URL": "https://api.binance.us/api/v3/klines",
    "TELEGRAM_TOKEN": "8333141058:AAGaMRuJBnnr2I2e13cqwklZKSEPzgkKIbc",
    "TELEGRAM_CHANNELS": {
        "free":    "-1003543150372",
        "starter": "-1003871305269",
        "pro":     "-1003832374485",
        "vip":     "-1003741068762",
    },
}

SUPA = CONFIG["SUPABASE_URL"]
KEY  = CONFIG["SUPABASE_KEY"]
HD   = {
    "apikey": KEY,
    "Authorization": "Bearer " + KEY,
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

_tg_cache = set()

def send_telegram(chat_id, text, cache_key=None):
    global _tg_cache
    if cache_key:
        k = str(chat_id)+":"+cache_key
        if k in _tg_cache:
            log.info("  TG skip dup: %s", cache_key); return
        _tg_cache.add(k)
    if len(text) > 4000:
        text = text[:3997]+"..."
    for attempt in range(1,4):
        try:
            r = requests.post(
                "https://api.telegram.org/bot"+CONFIG["TELEGRAM_TOKEN"]+"/sendMessage",
                json={"chat_id":chat_id,"text":text,"parse_mode":"HTML"},timeout=10)
            if r.status_code==200:
                log.info("  TG sent to %s", chat_id); return
            if r.status_code==400 and "parse" in r.text.lower():
                plain=text.replace("<b>","").replace("</b>","").replace("<i>","").replace("</i>","")
                requests.post("https://api.telegram.org/bot"+CONFIG["TELEGRAM_TOKEN"]+"/sendMessage",
                    json={"chat_id":chat_id,"text":plain},timeout=10)
                return
            log.warning("TG attempt %d failed: %d",attempt,r.status_code)
        except Exception as e:
            log.error("TG attempt %d error: %s",attempt,e)
        if attempt<3: time.sleep(1)


def build_signal_message(sig, status_type="new"):
    direction = sig.get("direction","")
    coin = sig.get("coin","")
    emoji = "🟢" if direction == "LONG" else "🔴"
    arrow = "📈" if direction == "LONG" else "📉"

    if status_type == "new":
        msg = (
            arrow + " <b>NEW SIGNAL — " + coin + "/USDT</b>\n\n"
            + emoji + " <b>Direction:</b> " + direction + "\n"
            + "🎯 <b>Confidence:</b> " + str(sig.get("confidence","")) + "%\n\n"
            + "💰 <b>Entry Zone:</b>\n"
            + "   $" + str(sig.get("entry_low","")) + " – $" + str(sig.get("entry_high","")) + "\n\n"
            + "🛑 <b>Stop Loss:</b>   $" + str(sig.get("sl","")) + "\n"
            + "✅ <b>TP1:</b>         $" + str(sig.get("tp1","")) + "\n"
            + "🏆 <b>TP2:</b>         $" + str(sig.get("tp2","")) + "\n\n"
            + "⚖️ <b>R:R Ratio:</b>  " + str(sig.get("rr","")) + "\n"
            + "⚠️ <b>Risk Level:</b> " + str(sig.get("risk","")) + "\n"
            + "⏱ <b>Valid:</b>       " + str(sig.get("valid_mins",360)) + " mins\n\n"
            + "🤖 <i>TradexoAI Signal Bot</i>\n"
            + "🌐 tradexoai.com"
        )
    elif status_type == "tp1":
        pnl = sig.get("pnl_pct","")
        msg = (
            "✅ <b>TP1 HIT — " + coin + "/USDT</b>\n\n"
            + "📈 <b>Direction:</b> " + direction + "\n"
            + "💵 <b>Entry:</b> $" + str(sig.get("entry_price","")) + "\n"
            + "🎯 <b>Exit:</b> $" + str(sig.get("exit_price","")) + "\n"
            + ("💰 <b>PnL:</b> +" + str(pnl) + "%\n" if pnl else "")
            + "\n💡 <i>Move SL to breakeven now 🔥</i>"
            + "\n🤖 <i>TradexoAI Signal Bot</i>"
        )
    elif status_type == "tp2":
        pnl = sig.get("pnl_pct","")
        msg = (
            "🏆 <b>TP2 HIT — " + coin + "/USDT</b>\n\n"
            + "📈 <b>Direction:</b> " + direction + "\n"
            + "💵 <b>Entry:</b> $" + str(sig.get("entry_price","")) + "\n"
            + "🎯 <b>Exit:</b> $" + str(sig.get("exit_price","")) + "\n"
            + ("💰 <b>PnL:</b> +" + str(pnl) + "%\n" if pnl else "")
            + "\n🔥 <i>Full target reached! Outstanding trade!</i>"
            + "\n🤖 <i>TradexoAI Signal Bot</i>"
        )
    elif status_type == "sl":
        pnl = sig.get("pnl_pct","")
        msg = (
            "🛑 <b>SL HIT — " + coin + "/USDT</b>\n\n"
            + "📉 <b>Direction:</b> " + direction + "\n"
            + "💵 <b>Entry:</b> $" + str(sig.get("entry_price","")) + "\n"
            + "❌ <b>Exit:</b> $" + str(sig.get("exit_price","")) + "\n"
            + ("📊 <b>PnL:</b> " + str(pnl) + "%\n" if pnl else "")
            + "\n⚠️ <i>Losses are part of trading. Risk management is key!</i>"
            + "\n🤖 <i>TradexoAI Signal Bot</i>"
        )
    return msg


def notify_all_channels(sig, status_type="new"):
    msg = build_signal_message(sig, status_type)
    channels = CONFIG["TELEGRAM_CHANNELS"]
    if status_type == "new":
        free_msg = (
            ("📈" if sig.get("direction")=="LONG" else "📉")
            + " <b>NEW SIGNAL: " + sig.get("coin","") + "/USDT</b>\n"
            + ("🟢" if sig.get("direction")=="LONG" else "🔴")
            + " " + sig.get("direction","") + " | Conf: " + str(sig.get("confidence","")) + "%\n\n"
            + "🔒 <i>Full details (Entry, SL, TP) available for paid members</i>\n"
            + "👉 tradexoai.com"
        )
        coin_k = sig.get("coin","")
        send_telegram(channels["free"], free_msg, cache_key="new_free:"+coin_k)
        time.sleep(0.3)
        for plan in ["starter","pro","vip"]:
            send_telegram(channels[plan], msg, cache_key="new_"+plan+":"+coin_k)
            time.sleep(0.2)
    else:
        coin_k2 = sig.get("coin","")
        for plan_n, chat_id in channels.items():
            send_telegram(chat_id, msg, cache_key=status_type+":"+plan_n+":"+coin_k2)
            time.sleep(0.2)
def get_klines(symbol, interval="15m", limit=150, retries=3):
    min_candles = min(limit, 50) if limit >= 50 else limit
    for attempt in range(1, retries+1):
        try:
            r = requests.get(CONFIG["BINANCE_URL"],
                params={"symbol": symbol+"USDT","interval":interval,"limit":limit},
                timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and len(data) >= min_candles:
                    return [{"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),
                             "close":float(c[4]),"volume":float(c[5])} for c in data]
                log.warning("Binance %s: insufficient data (%d candles)", symbol, len(data) if data else 0)
                return None
            if attempt < retries:
                log.warning("Binance %s attempt %d failed (%d), retrying...", symbol, attempt, r.status_code)
                time.sleep(1)
            else:
                log.warning("Binance %s all retries failed (%d)", symbol, r.status_code)
        except Exception as e:
            if attempt < retries:
                log.warning("Binance %s attempt %d error: %s, retrying...", symbol, attempt, e)
                time.sleep(1)
            else:
                log.error("Binance %s failed: %s", symbol, e)
    return None

def calc_ema_series(closes, p):
    if len(closes) < p:
        return []
    m = 2.0 / (p + 1)
    result = [None] * p
    v = sum(closes[:p]) / p
    result.append(v)
    for x in closes[p:]:
        v = (x - v) * m + v
        result.append(v)
    return result

def calc_ema(closes, p):
    s = calc_ema_series(closes, p)
    return s[-1] if s else None

def calc_rsi(closes, p=14):
    if len(closes) < p + 1:
        return None
    ag = al = 0.0
    for i in range(1, p+1):
        d = closes[i] - closes[i-1]
        ag += max(d, 0)
        al += abs(min(d, 0))
    ag /= p
    al /= p
    for i in range(p+1, len(closes)):
        d = closes[i] - closes[i-1]
        ag = (ag*(p-1) + max(d,0)) / p
        al = (al*(p-1) + abs(min(d,0))) / p
    return 100.0 if al == 0 else 100.0-(100.0/(1.0+ag/al))

def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal + 2:
        return None, None, None, None
    ema_fast = calc_ema_series(closes, fast)
    ema_slow = calc_ema_series(closes, slow)
    offset = slow - fast
    macd_vals = []
    for i in range(len(ema_slow)):
        fi = i + offset
        if fi < len(ema_fast) and ema_fast[fi] is not None and ema_slow[i] is not None:
            macd_vals.append(ema_fast[fi] - ema_slow[i])
    if len(macd_vals) < signal + 2:
        return None, None, None, None
    sig_series = calc_ema_series(macd_vals, signal)
    if len(sig_series) < 2:
        return None, None, None, None
    hist = macd_vals[-1] - sig_series[-1]
    prev_hist = macd_vals[-2] - sig_series[-2] if sig_series[-2] is not None else 0
    return macd_vals[-1], sig_series[-1], hist, prev_hist

def calc_bollinger(closes, p=20, mult=2.0):
    if len(closes) < p:
        return None, None, None
    mid = sum(closes[-p:]) / p
    std = (sum((x-mid)**2 for x in closes[-p:]) / p) ** 0.5
    return mid+mult*std, mid, mid-mult*std

def calc_atr(candles, p=14):
    if len(candles) < p+1:
        return None
    trs = [max(candles[i]["high"]-candles[i]["low"],
               abs(candles[i]["high"]-candles[i-1]["close"]),
               abs(candles[i]["low"]-candles[i-1]["close"]))
           for i in range(1, len(candles))]
    return sum(trs[-p:]) / p

def calc_adx(candles, p=14):
    if len(candles) < p*2+1:
        return None, None, None
    pdm_list, mdm_list, tr_list = [], [], []
    for i in range(1, len(candles)):
        h,l = candles[i]["high"],candles[i]["low"]
        ph,pl,pc = candles[i-1]["high"],candles[i-1]["low"],candles[i-1]["close"]
        up = h-ph
        dn = pl-l
        pdm_list.append(up if up>dn and up>0 else 0.0)
        mdm_list.append(dn if dn>up and dn>0 else 0.0)
        tr_list.append(max(h-l, abs(h-pc), abs(l-pc)))
    atr_w = sum(tr_list[:p])
    pdm_w = sum(pdm_list[:p])
    mdm_w = sum(mdm_list[:p])
    dx_vals = []
    for i in range(p, len(tr_list)):
        atr_w = atr_w - atr_w/p + tr_list[i]
        pdm_w = pdm_w - pdm_w/p + pdm_list[i]
        mdm_w = mdm_w - mdm_w/p + mdm_list[i]
        if atr_w == 0:
            continue
        pdi = pdm_w/atr_w*100
        mdi = mdm_w/atr_w*100
        denom = pdi+mdi
        dx_vals.append(abs(pdi-mdi)/denom*100 if denom>0 else 0)
    if len(dx_vals) < p:
        return None, None, None
    adx_v = sum(dx_vals[-p:]) / p
    pdi = pdm_w/atr_w*100 if atr_w else 0
    mdi = mdm_w/atr_w*100 if atr_w else 0
    return adx_v, pdi, mdi

def calc_sr(candles, lookback=50):
    h = [c["high"] for c in candles[-lookback:]]
    l = [c["low"]  for c in candles[-lookback:]]
    return min(l), max(h)

def calc_candle(candles):
    if len(candles) < 2:
        return 0
    c,p = candles[-1],candles[-2]
    body  = abs(c["close"]-c["open"])
    upper = c["high"]-max(c["close"],c["open"])
    lower = min(c["close"],c["open"])-c["low"]
    if lower>body*2 and upper<body*0.5 and c["close"]>c["open"]: return 1
    if upper>body*2 and lower<body*0.5 and c["close"]<c["open"]: return -1
    if (c["close"]>c["open"] and p["close"]<p["open"] and c["open"]<p["close"] and c["close"]>p["open"]): return 1
    if (c["close"]<c["open"] and p["close"]>p["open"] and c["open"]>p["close"] and c["close"]<p["open"]): return -1
    return 0

def calc_volume_surge(candles, lookback=20):
    if len(candles)<lookback+1: return 0.0
    avg = sum(c["volume"] for c in candles[-lookback-1:-1])/lookback
    curr = candles[-1]["volume"]
    if avg==0: return 0.0
    if curr>avg*1.5: return 1.0
    if curr>avg*1.2: return 0.5
    return 0.0

def get_4h_trend(coin):
    try:
        kl = get_klines(coin, "4h", 60)
        if not kl or len(kl) < 50: return 0
        closes = [k["close"] for k in kl]
        e20 = calc_ema(closes, 20)
        e50 = calc_ema(closes, 50)
        if not e20 or not e50: return 0
        price = closes[-1]
        if e20 > e50 and price > e20: return 1
        elif e20 < e50 and price < e20: return -1
        return 0
    except Exception as e:
        log.error("4H trend %s: %s", coin, e)
        return 0

def detect_rsi_divergence(closes, rsi_vals):
    try:
        if len(closes) < 20 or len(rsi_vals) < 20: return 0
        prices = closes[-20:]
        rsis = rsi_vals[-20:]
        p_low_idx = prices.index(min(prices))
        p_high_idx = prices.index(max(prices))
        if p_low_idx > 10:
            prev_low = min(prices[:p_low_idx-2])
            prev_low_idx = prices[:p_low_idx-2].index(prev_low)
            if prices[p_low_idx] < prev_low and rsis[p_low_idx] > rsis[prev_low_idx]:
                return 1
        if p_high_idx > 10:
            prev_high = max(prices[:p_high_idx-2])
            prev_high_idx = prices[:p_high_idx-2].index(prev_high)
            if prices[p_high_idx] > prev_high and rsis[p_high_idx] < rsis[prev_high_idx]:
                return -1
        return 0
    except:
        return 0

def find_swing_levels(klines, lookback=10):
    if not klines or len(klines) < lookback: return None, None
    highs = [k["high"] for k in klines[-lookback:]]
    lows = [k["low"] for k in klines[-lookback:]]
    return max(highs), min(lows)

def get_order_book_signal(symbol):
    try:
        r = requests.get(CONFIG["BINANCE_URL"].replace('/klines','') + '/depth',
            params={"symbol": symbol+"USDT", "limit": 20}, timeout=8)
        if r.status_code != 200: return 0.0
        book = r.json()
        bid_vol = sum(float(b[1]) for b in book.get('bids', [])[:10])
        ask_vol = sum(float(a[1]) for a in book.get('asks', [])[:10])
        total = bid_vol + ask_vol
        if total == 0: return 0.0
        ratio = bid_vol / total
        if ratio > 0.65:   return 1.5
        elif ratio > 0.55: return 0.75
        elif ratio < 0.35: return -1.5
        elif ratio < 0.45: return -0.75
        return 0.0
    except Exception as e:
        log.error("OrderBook %s: %s", symbol, e)
        return 0.0

def get_funding_rate(symbol):
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex",
            params={"symbol": symbol+"USDT"}, timeout=8)
        if r.status_code != 200: return 0.0
        data = r.json()
        rate = float(data.get('lastFundingRate', 0)) * 100
        if rate < -0.05:   return 1.5
        elif rate < -0.01: return 0.75
        elif rate > 0.05:  return -1.5
        elif rate > 0.01:  return -0.75
        return 0.0
    except:
        return 0.0

def position_size(price, sl):
    risk_amt = CONFIG["CAPITAL"] * CONFIG["RISK_PCT"]
    sl_dist = abs(price - sl)
    if sl_dist == 0: return 0
    return round(risk_amt / sl_dist, 6)

def passes_filters(coin, adx_v, atr_v, price, ema20, ema50, direction):
    if adx_v < 23:
        log.info("  %s filtered: ADX %.1f low", coin, adx_v); return False
    if (atr_v/price)*100 < 0.15:
        log.info("  %s filtered: low volatility", coin); return False
    if direction=="LONG"  and ema20<ema50:
        log.info("  %s filtered: LONG in downtrend", coin); return False
    if direction=="SHORT" and ema20>ema50:
        log.info("  %s filtered: SHORT in uptrend", coin); return False
    return True
def get_market_regime():
    try:
        candles = get_klines("BTC", "1h", 210)
        if not candles or len(candles) < 200:
            return "neutral"
        closes = [x["close"] for x in candles]
        ema200 = calc_ema(closes, 200)
        price = closes[-1]
        if price > ema200 * 1.02:
            log.info("Market regime: BULL (BTC %.0f > EMA200 %.0f)", price, ema200)
            return "bull"
        elif price < ema200 * 0.98:
            log.info("Market regime: BEAR (BTC %.0f < EMA200 %.0f)", price, ema200)
            return "bear"
        else:
            log.info("Market regime: NEUTRAL (BTC %.0f ~ EMA200 %.0f)", price, ema200)
            return "neutral"
    except Exception as e:
        log.error("Market regime error: %s", e)
        return "neutral"

def calculate_valid_mins(atr_v, price, adx_v):
    atr_pct = (atr_v / price) * 100 if price > 0 else 0
    base = 120
    if atr_pct > 2:   base -= 30
    elif atr_pct < 1: base += 30
    if adx_v > 30:    base += 20
    elif adx_v < 18:  base -= 20
    return max(60, min(base, 360))

def analyze(coin, regime="neutral"):
    c15 = get_klines(coin, "15m", 200)
    c1h = get_klines(coin, "1h", 100)
    if not c15 or len(c15)<80: return None
    closes15 = [c["close"] for c in c15]
    price = closes15[-1]
    rsi15 = calc_rsi(closes15)
    ml,ms,hist15,ph = calc_macd(closes15)
    bb_up,bb_mid,bb_lo = calc_bollinger(closes15)
    ema20 = calc_ema(closes15,20)
    ema50 = calc_ema(closes15,50)
    atr_v = calc_atr(c15)
    adx_r = calc_adx(c15)
    supp,resist = calc_sr(c15)
    csig = calc_candle(c15)
    vsurge = calc_volume_surge(c15)
    if not all([rsi15,atr_v,ema20,ema50]): return None
    ob_signal = get_order_book_signal(coin)
    fr_signal = get_funding_rate(coin)
    trend4h = get_4h_trend(coin)
    rsi_vals = []
    for _i in range(20, len(closes15)):
        _r = calc_rsi(closes15[:_i+1])
        if _r is not None: rsi_vals.append(_r)
    divergence = detect_rsi_divergence(closes15[-len(rsi_vals):], rsi_vals) if rsi_vals else 0
    adx_v = adx_r[0] if adx_r and adx_r[0] else 20.0
    pdi   = adx_r[1] if adx_r and adx_r[1] else 0.0
    mdi   = adx_r[2] if adx_r and adx_r[2] else 0.0
    strong = adx_v >= 25
    trend1h=0; rsi1h=50.0
    if c1h and len(c1h)>=50:
        cl1h=[c["close"] for c in c1h]
        rsi1h=calc_rsi(cl1h) or 50.0
        e20_1h=calc_ema(cl1h,20); e50_1h=calc_ema(cl1h,50)
        p1h=cl1h[-1]
        if e20_1h and e50_1h:
            if e20_1h>e50_1h and p1h>e20_1h: trend1h=1
            elif e20_1h<e50_1h and p1h<e20_1h: trend1h=-1
    bull=bear=0.0
    if rsi15<25:     bull+=2.0
    elif rsi15<35:   bull+=1.5
    elif rsi15<45:   bull+=0.5
    elif rsi15>75:   bear+=2.0
    elif rsi15>65:   bear+=1.5
    elif rsi15>55:   bear+=0.5
    if hist15 is not None and ph is not None:
        if hist15>0 and ph<=0:   bull+=2.0
        elif hist15>0:           bull+=0.5
        elif hist15<0 and ph>=0: bear+=2.0
        elif hist15<0:           bear+=0.5
    if bb_up and bb_lo and bb_up>bb_lo:
        if price<=bb_lo:   bull+=1.5
        elif price>=bb_up: bear+=1.5
        else:
            bp=(price-bb_lo)/(bb_up-bb_lo)
            if bp<0.25: bull+=0.5
            elif bp>0.75: bear+=0.5
    if ema20>ema50 and price>ema20:   bull+=1.0
    elif ema20<ema50 and price<ema20: bear+=1.0
    if strong:
        if pdi>mdi: bull+=1.5
        else:       bear+=1.5
    else:
        if pdi>mdi: bull+=0.5
        else:       bear+=0.5
    if trend1h==1:    bull+=1.5
    elif trend1h==-1: bear+=1.5
    if rsi1h<40:   bull+=0.5
    elif rsi1h>60: bear+=0.5
    if csig==1:    bull+=1.0
    elif csig==-1: bear+=1.0
    if vsurge>0:
        if bull>=bear: bull+=vsurge
        else:          bear+=vsurge
    sr_r=resist-supp
    if sr_r>0:
        sp=(price-supp)/sr_r
        if sp<0.1:   bull+=1.0
        elif sp>0.9: bear+=1.0
    if ob_signal > 0:   bull += ob_signal
    elif ob_signal < 0: bear += abs(ob_signal)
    if fr_signal > 0:   bull += fr_signal
    elif fr_signal < 0: bear += abs(fr_signal)
    if regime=="bull" and bull>bear:   bull+=0.5
    elif regime=="bear" and bear>bull: bear+=0.5
    if trend4h == 1:    bull += 1.5
    elif trend4h == -1: bear += 1.5
    if divergence == 1:    bull += 2.0
    elif divergence == -1: bear += 2.0
    if trend1h == (1 if bull > bear else -1):
        if bull > bear: bull += 1.2
        else: bear += 1.2
    if strong and trend1h == (1 if bull > bear else -1) and vsurge > 0:
        if bull > bear: bull += 1.0
        else: bear += 1.0
    base_score = max(bull, bear)
    if strong:
        conf = int((base_score / 11.5) * 100)
    else:
        conf = int((base_score / 13.5) * 100)
    if trend1h != 0: conf += 3
    if vsurge > 0:   conf += 2
    conf = min(conf, 95)
    log.info("  %s p=%.4f rsi=%.1f adx=%.1f 4h=%d div=%d ob=%.1f fr=%.1f bull=%.1f bear=%.1f conf=%d%%",
             coin,price,rsi15,adx_v,trend4h,divergence,ob_signal,fr_signal,bull,bear,conf)
    if adx_v >= 30:   min_score = 8.0
    elif adx_v >= 25: min_score = 7.5
    else:             min_score = 7.0
    if bull >= min_score and bull > bear:   direction,action="LONG","BUY"
    elif bear >= min_score and bear > bull: direction,action="SHORT","SELL"
    else:
        log.info("  %s: score too low (%.1f < %.1f)",coin,max(bull,bear),min_score); return None
    if direction == "LONG" and trend4h == -1:
        log.info("  %s: LONG rejected - 4H downtrend",coin); return None
    if direction == "SHORT" and trend4h == 1:
        log.info("  %s: SHORT rejected - 4H uptrend",coin); return None
    if not passes_filters(coin,adx_v,atr_v,price,ema20,ema50,direction): return None
    c5 = get_klines(coin,"5m",50)
    if c5 and len(c5)>=25:
        closes5 = [x["close"] for x in c5]
        ema9_5m = calc_ema(closes5,9)
        ema21_5m = calc_ema(closes5,21)
        p5 = closes5[-1]
        if direction=="LONG" and not(p5>ema9_5m and ema9_5m>ema21_5m):
            log.info("  %s 5m rejected",coin); return None
        if direction=="SHORT" and not(p5<ema9_5m and ema9_5m<ema21_5m):
            log.info("  %s 5m rejected",coin); return None
        log.info("  %s 5m confirmed: %s",coin,direction)
    dec=2 if price>100 else (4 if price>1 else 6)
    sl_m  =CONFIG["ATR_SL_MULT_STRONG"]  if strong else CONFIG["ATR_SL_MULT_WEAK"]
    tp1_m =CONFIG["ATR_TP1_MULT_STRONG"] if strong else CONFIG["ATR_TP1_MULT_WEAK"]
    tp2_m =CONFIG["ATR_TP2_MULT_STRONG"] if strong else CONFIG["ATR_TP2_MULT_WEAK"]
    _swing_h, _swing_l = find_swing_levels(c15, 10)
    if direction=="LONG":
        atr_sl = price - (atr_v * sl_m)
        if _swing_l and _swing_l < price and _swing_l > atr_sl:
            sl_p = _swing_l - (atr_v * 0.3)
        else:
            sl_p = atr_sl
        tp1 = price + (atr_v * tp1_m)
        tp2 = price + (atr_v * tp2_m)
    else:
        atr_sl = price + (atr_v * sl_m)
        if _swing_h and _swing_h > price and _swing_h < atr_sl:
            sl_p = _swing_h + (atr_v * 0.3)
        else:
            sl_p = atr_sl
        tp1 = price - (atr_v * tp1_m)
        tp2 = price - (atr_v * tp2_m)
    risk=abs(price-sl_p)
    rr=round(abs(tp1-price)/risk,1) if risk>0 else 2.0
    ap=(atr_v/price)*100
    rl="LOW RISK" if ap<1.5 else ("MEDIUM RISK" if ap<3 else "HIGH RISK")
    pos_size=position_size(price,sl_p)
    return {
        "coin":coin,"action":action,"direction":direction,
        "confidence":int(conf),"entry_price":round(price,dec),
        "entry_low":round(price*0.999,dec),"entry_high":round(price*1.001,dec),
        "sl":round(sl_p,dec),"tp1":round(tp1,dec),"tp2":round(tp2,dec),
        "rr":"1:"+str(rr),"risk":rl,"position_size":pos_size,
        "valid_mins":calculate_valid_mins(atr_v,price,adx_v),"status":"ACTIVE","source":"ai_bot_v5"
    }

def expire_old_signals():
    try:
        r = requests.get(SUPA+"/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin,direction,created_at,valid_mins",headers=HD,timeout=10)
        if r.status_code != 200:
            log.error("expire fetch failed: %d", r.status_code); return
        now = datetime.datetime.utcnow()
        expired_count = 0
        for sig in r.json():
            cs = sig.get("created_at",""); vm = sig.get("valid_mins") or 360
            if not cs: continue
            try:
                created = datetime.datetime.strptime(cs[:19],"%Y-%m-%dT%H:%M:%S")
                age = (now - created).total_seconds() / 60
                if age > vm:
                    patch_r = requests.patch(
                        SUPA+"/rest/v1/bot_signals?id=eq."+str(sig["id"]),
                        headers=HD, json={"status":"CLOSED"}, timeout=10)
                    if patch_r.status_code in (200,201,204):
                        log.info("  EXPIRED: %s (%.0fmin)", sig["coin"], age)
                        expired_count += 1
            except Exception as e:
                log.error("Expiry error: %s", e)
        if expired_count:
            log.info("Expired %d signals", expired_count)
    except Exception as e:
        log.error("expire_old_signals: %s", e)

def update_active_signals():
    try:
        r = requests.get(SUPA+"/rest/v1/bot_signals?status=eq.ACTIVE&select=*",headers=HD,timeout=10)
        if r.status_code != 200: return
        active = r.json()
        log.info("Monitoring %d active signals", len(active))
        for sig in active:
            coin=sig.get("coin"); direction=sig.get("direction")
            sl=sig.get("sl"); tp1=sig.get("tp1"); tp2=sig.get("tp2"); entry=sig.get("entry_price")
            if not all([coin,direction,sl,tp1]): continue
            candles=get_klines(coin,"15m",5)
            if not candles: continue
            curr=candles[-1]["close"]
            new_status=None
            if direction=="LONG":
                if tp2 and curr>=float(tp2):   new_status="TP2_HIT"
                elif curr>=float(tp1):         new_status="TP1_HIT"
                elif curr<=float(sl):          new_status="SL_HIT"
            else:
                if tp2 and curr<=float(tp2):   new_status="TP2_HIT"
                elif curr<=float(tp1):         new_status="TP1_HIT"
                elif curr>=float(sl):          new_status="SL_HIT"
            if new_status:
                pnl_pct=None
                ep_val = entry or sig.get("entry_low") or sig.get("entry_high")
                if ep_val:
                    ep=float(ep_val)
                    if ep>0:
                        pnl_pct=round(((curr-ep)/ep)*100,2) if direction=="LONG" else round(((ep-curr)/ep)*100,2)
                already_notified = sig.get("tg_notified", False)
                patch_data = {"status":new_status,"exit_price":round(curr,6),"pnl_pct":pnl_pct,"tg_notified":True}
                requests.patch(SUPA+"/rest/v1/bot_signals?id=eq."+str(sig["id"]),
                    headers=HD,json=patch_data,timeout=10)
                log.info("  %s %s -> %s PnL:%s%%",coin,direction,new_status,pnl_pct)
                if not already_notified:
                    updated=dict(sig); updated["exit_price"]=round(curr,6); updated["pnl_pct"]=pnl_pct
                    st="tp2" if new_status=="TP2_HIT" else ("tp1" if new_status=="TP1_HIT" else "sl")
                    notify_all_channels(updated,st)
            time.sleep(0.2)
    except Exception as e:
        log.error("Monitor: %s",e)

def log_performance_stats():
    try:
        r = requests.get(
            SUPA+"/rest/v1/bot_signals?status=in.(TP1_HIT,SL_HIT,TP2_HIT)&select=status,pnl_pct&order=created_at.desc&limit=100",
            headers=HD, timeout=10)
        if r.status_code != 200: return
        closed = r.json()
        if not closed:
            log.info("Stats: no closed trades yet"); return
        total = len(closed)
        wins   = [t for t in closed if t.get("status") in ("TP1_HIT","TP2_HIT")]
        losses = [t for t in closed if t.get("status")=="SL_HIT"]
        win_rate = round(len(wins)/total*100,1) if total>0 else 0
        pnl_vals = [t.get("pnl_pct") for t in closed if t.get("pnl_pct") is not None]
        total_pnl = round(sum(pnl_vals),2) if pnl_vals else 0
        gross_profit = sum(p for p in pnl_vals if p>0)
        gross_loss   = abs(sum(p for p in pnl_vals if p<0))
        pf = round(gross_profit/gross_loss,2) if gross_loss>0 else 0
        log.info("=== STATS: Trades=%d | WinRate=%.1f%% | PnL=%.2f%% | PF=%.2f | W/L=%d/%d ===",
                 total,win_rate,total_pnl,pf,len(wins),len(losses))
    except Exception as e:
        log.error("Stats error: %s", e)

def get_active():
    try:
        r = requests.get(
            SUPA+"/rest/v1/bot_signals?status=eq.ACTIVE&select=id,coin&order=created_at.desc",
            headers=HD, timeout=10)
        if r.status_code==200: return r.json()
    except Exception as e:
        log.error("get_active: %s", e)
    return []

def post_signal(sig):
    try:
        r = requests.post(SUPA+"/rest/v1/bot_signals", headers=HD, json=sig, timeout=10)
        if r.status_code in (200,201,204):
            log.info("  POSTED %s %s %d%%", sig["coin"],sig["direction"],sig["confidence"])
            notify_all_channels(sig, "new")
        else:
            log.error("  FAIL %s: %s", sig["coin"], r.text)
    except Exception as e:
        log.error("post: %s", e)

def close_old_signals(active):
    if len(active)<=CONFIG["MAX_ACTIVE"]: return
    for old in active[CONFIG["MAX_ACTIVE"]:]:
        try:
            requests.patch(SUPA+"/rest/v1/bot_signals?id=eq."+str(old["id"]),
                           headers=HD, json={"status":"CLOSED"}, timeout=10)
            log.info("  Closed: %s", old["coin"])
        except Exception as e:
            log.error("close: %s", e)

def main():
    log.info("="*55)
    log.info("TradexoAI Bot v6 | %s", datetime.datetime.utcnow())
    log.info("Coins:%d | MinScore:%.1f | Capital:$%.0f | Risk:%.0f%%",
             len(CONFIG["COINS"]),CONFIG["MIN_SCORE"],CONFIG["CAPITAL"],CONFIG["RISK_PCT"]*100)
    log_performance_stats()
    expire_old_signals()
    update_active_signals()
    active = get_active()
    active_coins = [s["coin"] for s in active]
    log.info("Active: %d", len(active))
    regime = get_market_regime()
    new_sigs = []
    for coin in CONFIG["COINS"]:
        if coin in active_coins:
            log.info("Skip: %s", coin)
            continue
        log.info("Scan: %s", coin)
        sig = analyze(coin, regime)
        time.sleep(CONFIG["SLEEP"])
        if sig:
            log.info("*** %s %s %d%% ***", sig["coin"],sig["direction"],sig["confidence"])
            new_sigs.append(sig)
    log.info("New signals: %d", len(new_sigs))
    for sig in new_sigs:
        post_signal(sig)
    close_old_signals(get_active())
    log.info("Done! Active: %d", len(get_active()))
    log.info("="*55)

main()
