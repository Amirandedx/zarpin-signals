import json
import math
import os
import time
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
STATE_FILE = "state.json"

# --- منبع قیمت لحظه‌ای ---
BOORSI_URL = "https://api.boorsi.net/api/charting/dossier/%D8%B7%D9%84%D8%A7%20%DB%B1%DB%B8%20%D8%B9%DB%8C%D8%A7%D8%B1"

# --- منبع کندل‌ها برای تشخیص خودکار کف، سقف و RSI (منطق daric_bot.py) ---
DARIC_HISTORY_URL = "https://apie.daric.gold/public/chart/history"
DARIC_RESOLUTION = "60"
DARIC_COUNTBACK = 120

PIVOT_LEFT = 3
PIVOT_RIGHT = 3
LOOKBACK_CANDLES = 60
ZONE_TOLERANCE_PCT = 0.0025      # تلرانس نزدیکی به کف (0.25%)
MIN_BREAKOUT_GAIN_PCT = 0.0025   # حداقل عبور از سقف برای شکست معتبر (0.25%)
RSI_OVERBOUGHT = 72.0
RSI_OVERSOLD_REBOUND = 55.0

# --- تنظیمات کارمزد و حد سود/ضرر ---
BUY_FEE_PCT = 0.005          # 0.5% کارمزد خرید
SELL_FEE_PCT = 0.005         # 0.5% کارمزد فروش (1% مجموع رفت و برگشت)
TARGET_NET_AFTER_BE = 0.01   # +1% سود خالص قطعی بعد از نقطه سر‌به‌سر
FALLBACK_SL_PCT = 0.015      # 1.5% حد ضرر پیش‌فرض


def fmt(x):
    return "{:,.0f}".format(x)


def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"Telegram HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"Telegram send error: {e}")


def _parse_number(val):
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("٬", "").replace(" ", "")
    if not s:
        return None
    return float(s)


def get_live_price():
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://boorsi.net/",
        "Origin": "https://boorsi.net",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    try:
        r = requests.get(BOORSI_URL, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:150]}"

        data = r.json()
        if not isinstance(data, dict):
            return None, "ساختار JSON نامعتبر است."

        quote = data.get("quote") if isinstance(data.get("quote"), dict) else data
        raw_price = None
        for key in ("price", "lastPrice", "close", "previousClose"):
            if isinstance(quote, dict) and quote.get(key) is not None:
                val = _parse_number(quote.get(key))
                if val is not None and math.isfinite(val) and val > 0:
                    raw_price = val
                    break

        if raw_price is None:
            return None, "قیمت معتبر در quote یافت نشد."

        currency = str(data.get("currency", "")).upper()
        if currency == "IRR" or raw_price > 50_000_000:
            price_toman = raw_price / 10.0
        else:
            price_toman = raw_price

        if price_toman < 20_000_000 or price_toman > 35_000_000:
            return None, f"قیمت خارج از بازه مجاز: {price_toman:,.0f}"

        return price_toman, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def calc_rsi(closes, period=14):
    if len(closes) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / float(period)
    avg_loss = sum(losses[:period]) / float(period)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / float(period)
        avg_loss = (avg_loss * (period - 1) + losses[i]) / float(period)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def detect_floor_and_ceiling(highs, lows, closes):
    n = len(closes)
    start_idx = max(PIVOT_LEFT, n - LOOKBACK_CANDLES)
    end_idx = n - PIVOT_RIGHT

    swing_highs = []
    swing_lows = []

    for i in range(start_idx, end_idx):
        h_val = highs[i]
        l_val = lows[i]
        is_high = all(h_val >= highs[j] for j in range(i - PIVOT_LEFT, i + PIVOT_RIGHT + 1) if j != i)
        is_low = all(l_val <= lows[j] for j in range(i - PIVOT_LEFT, i + PIVOT_RIGHT + 1) if j != i)
        if is_high:
            swing_highs.append(h_val)
        if is_low:
            swing_lows.append(l_val)

    last_price = closes[-1]

    ceilings_above = [h for h in swing_highs if h > last_price * 0.998]
    if ceilings_above:
        ceiling = min(ceilings_above)
    elif swing_highs:
        ceiling = max(swing_highs[-3:])
    else:
        ceiling = max(highs[-min(len(highs), 20):])

    floors_below = [l for l in swing_lows if l < last_price * 1.002]
    if floors_below:
        floor = max(floors_below)
    elif swing_lows:
        floor = min(swing_lows[-3:])
    else:
        floor = min(lows[-min(len(lows), 20):])

    if floor >= ceiling:
        floor = min(lows[-min(len(lows), 15):])
        ceiling = max(highs[-min(len(highs), 15):])

    return floor, ceiling


def fetch_chart_analysis():
    now = int(time.time())
    params = {
        "symbol": "GOLD18TMN",
        "resolution": DARIC_RESOLUTION,
        "from": now - 86400 * 14,
        "to": now,
        "countback": DARIC_COUNTBACK,
        "currencyCode": "TMN",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://market.daric.gold/",
    }
    try:
        r = requests.get(DARIC_HISTORY_URL, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("s") != "ok":
            return None, f"daric status={data.get('s')}"

        closes = [float(x) for x in data.get("c", []) if x is not None and math.isfinite(float(x)) and float(x) > 0]
        highs = [float(x) for x in data.get("h", []) if x is not None and math.isfinite(float(x)) and float(x) > 0]
        lows = [float(x) for x in data.get("l", []) if x is not None and math.isfinite(float(x)) and float(x) > 0]

        min_len = max(PIVOT_LEFT + PIVOT_RIGHT + 2, 16)
        if len(closes) < min_len or len(highs) < min_len or len(lows) < min_len:
            return None, f"کندل کافی نیست ({len(closes)})"

        floor, ceiling = detect_floor_and_ceiling(highs, lows, closes)
        rsi_val = calc_rsi(closes, period=14)

        return {
            "floor": floor,
            "ceiling": ceiling,
            "prev_close": closes[-2],
            "last_close": closes[-1],
            "rsi": rsi_val,
        }, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def calc_exit_levels(entry_price):
    effective_buy_cost = entry_price * (1.0 + BUY_FEE_PCT)
    breakeven_price = effective_buy_cost / (1.0 - SELL_FEE_PCT)
    tp1_price = breakeven_price * (1.0 + TARGET_NET_AFTER_BE)
    tp2_price = tp1_price * 1.005
    sl_price = entry_price * (1.0 - FALLBACK_SL_PCT)
    return breakeven_price, tp1_price, tp2_price, sl_price


def net_profit_toman(entry_price, current_price):
    total_buy_cost = entry_price * (1.0 + BUY_FEE_PCT)
    net_sell_proceeds = current_price * (1.0 - SELL_FEE_PCT)
    return net_sell_proceeds - total_buy_cost


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"position": None, "last_price": None}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"position": None, "last_price": None}
        pos = data.get("position")
        if isinstance(pos, dict) and pos.get("entry"):
            pos = {
                "entry": float(pos["entry"]),
                "tp1_alerted": bool(pos.get("tp1_alerted", False)),
            }
        else:
            pos = None
        last_p = data.get("last_price")
        last_p = float(last_p) if last_p is not None else None
        return {"position": pos, "last_price": last_p}
    except Exception:
        return {"position": None, "last_price": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def evaluate_buy(price, prev_price, chart):
    if not chart:
        return None

    rsi = chart.get("rsi")
    if rsi is not None and rsi >= RSI_OVERBOUGHT:
        return None

    ref_prev = prev_price if prev_price is not None else chart.get("prev_close", price)
    floor = chart["floor"]
    ceiling = chart["ceiling"]

    floor_low = floor * (1.0 - ZONE_TOLERANCE_PCT)
    floor_high = floor * (1.0 + ZONE_TOLERANCE_PCT)
    near_floor = (floor_low <= price <= floor_high) or (floor_low <= ref_prev <= floor_high)
    rebounding_from_floor = near_floor and (price > ref_prev) and (rsi is None or rsi < RSI_OVERSOLD_REBOUND)

    if rebounding_from_floor:
        return f"برگشت از کف معتبر (~{fmt(floor)})"

    brk_level = ceiling * (1.0 + MIN_BREAKOUT_GAIN_PCT)
    if ref_prev < brk_level <= price:
        return f"شکست سقف معتبر (~{fmt(ceiling)})"

    return None


def main():
    price, err = get_live_price()
    if price is None:
        send_telegram(f"⚠️ خطا در دریافت قیمت لحظه‌ای:\n<code>{err}</code>")
        return

    chart, chart_err = fetch_chart_analysis()
    state = load_state()
    prev_price = state.get("last_price")
    pos = state.get("position")

    if pos:
        entry = pos["entry"]
        be, tp1, tp2, sl = calc_exit_levels(entry)
        net_tmn = net_profit_toman(entry, price)

        if price <= sl:
            send_telegram(
                f"🔴 <b>سیگنال فروش (حد ضرر / SL)</b>\n"
                f"💰 قیمت فعلی: <b>{fmt(price)}</b> تومان\n"
                f"📥 قیمت ورود: {fmt(entry)} تومان\n"
                f"📉 سود/زیان خالص ۱ گرم: <b>{net_tmn:+,.0f}</b> تومان\n"
                f"⚡ سریع اقدام به فروش کنید."
            )
            state["position"] = None

        elif price >= tp2:
            send_telegram(
                f"🟢🟢 <b>سیگنال فروش (هدف دوم / TP2)</b>\n"
                f"💰 قیمت فعلی: <b>{fmt(price)}</b> تومان\n"
                f"📥 قیمت ورود: {fmt(entry)} تومان\n"
                f"📈 سود خالص ۱ گرم: <b>{net_tmn:+,.0f}</b> تومان\n"
                f"⚡ سریع اقدام به فروش کنید."
            )
            state["position"] = None

        elif price >= tp1 and not pos.get("tp1_alerted"):
            pos["tp1_alerted"] = True
            state["position"] = pos
            send_telegram(
                f"🟢 <b>سیگنال فروش (TP1: +1% سود خالص بعد از سر‌به‌سر)</b>\n"
                f"💰 قیمت فعلی: <b>{fmt(price)}</b> تومان\n"
                f"📥 قیمت ورود: {fmt(entry)} تومان | ⚖️ سر‌به‌سر: {fmt(be)} تومان\n"
                f"📈 سود خالص ۱ گرم الان: <b>{net_tmn:+,.0f}</b> تومان\n"
                f"🎯 هدف بعدی (TP2): {fmt(tp2)} تومان"
            )
    else:
        signal = evaluate_buy(price, prev_price, chart)
        if signal:
            be, tp1, tp2, sl = calc_exit_levels(price)
            p1_net = net_profit_toman(price, tp1)
            sl_net = net_profit_toman(price, sl)
            rsi_txt = f"RSI: {chart['rsi']:.1f}" if (chart and chart.get("rsi") is not None) else "RSI: N/A"
            floor_txt = fmt(chart["floor"]) if chart else "-"
            ceil_txt = fmt(chart["ceiling"]) if chart else "-"

            send_telegram(
                f"🟢 <b>سیگنال خرید معتبر [{signal}]</b>\n"
                f"💰 قیمت لحظه‌ای: <b>{fmt(price)}</b> تومان | {rsi_txt}\n"
                f"🧱 کف تشخیص‌داده‌شده: <b>{floor_txt}</b> | سقف: <b>{ceil_txt}</b>\n"
                f"⚖️ نقطه سر‌به‌سر (۱٪ کارمزد رفت‌وآمد): <b>{fmt(be)}</b> تومان\n"
                f"🎯 هدف فروش TP1 (+1% سود خالص): <b>{fmt(tp1)}</b> ({p1_net:+,.0f} ت)\n"
                f"🛑 حد ضرر SL: <b>{fmt(sl)}</b> ({sl_net:+,.0f} ت)"
            )
            # ثبت پوزیشن برای رصد خودکار حد سود و حد ضرر در اجراهای بعدی
            state["position"] = {"entry": price, "tp1_alerted": False}

    state["last_price"] = price
    save_state(state)
    if chart_err:
        print(f"Chart warning: {chart_err}")


if __name__ == "__main__":
    main()
