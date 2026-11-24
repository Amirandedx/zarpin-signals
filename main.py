import os
import json
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# --- حالت تست ---
# True = فقط قیمت لحظه‌ای و سطوح محاسبه‌شده را می‌فرستد و سیگنال خرید/فروش نمی‌دهد
TEST_MODE = True

# --- تنظیمات کارمزد و حد سود/ضرر ---
# مجموع کارمزد رفت و برگشت = 1% (0.5% خرید + 0.5% فروش)
BUY_FEE_PCT = 0.005
SELL_FEE_PCT = 0.005

# سود خالص قطعی بعد از رسیدن به نقطه سر‌به‌سر (1% = 0.01)
NET_PROFIT_PCT = 0.01

# حد ضرر درصدی نسبت به قیمت ورود (1.5% = 0.015)
SL_PCT = 0.015

# --- محدوده‌های قیمت خرید (نمونه هماهنگ با حوالی 25.4M؛ در صورت نیاز با چارت روز تنظیم کنید) ---
LOW_ZONE_MIN = 25150000
LOW_ZONE_MAX = 25250000
BREAKOUT_PRICE = 25650000


def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")


def get_price():
    try:
        url = "https://api.wallgold.ir/api/v1/markets"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:120]}"

        data = r.json()
        items = (
            data.get("result", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )

        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", ""))
            en_name = str(item.get("enName", ""))
            base_asset = str(item.get("baseAsset", ""))

            if (
                "GLD_18C" in symbol
                or "750" in symbol
                or "18C" in en_name
                or "750" in base_asset
            ):
                raw_price = (
                    item.get("lastPrice")
                    or item.get("lastBuyPrice")
                    or item.get("price")
                )
                if raw_price is not None and str(raw_price).strip() != "":
                    return float(str(raw_price).replace(",", "")), None

        return None, f"آیتم طلای ۱۸ عیار یافت نشد (تعداد آیتم‌ها: {len(items)})"

    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def calc_exit_levels(entry_price):
    """
    محاسبه نقطه سر‌به‌سر و قیمت فروش با سود خالص پس از کسر کارمزد خرید و فروش:
    - هزینه موثر خرید = entry * (1 + BUY_FEE_PCT)
    - قیمت سر‌به‌سر = هزینه موثر خرید / (1 - SELL_FEE_PCT)
    - قیمت هدف فروش (پس از سر‌به‌سر + سود خالص) = breakeven * (1 + NET_PROFIT_PCT)
    """
    effective_buy_cost = entry_price * (1 + BUY_FEE_PCT)
    breakeven_price = effective_buy_cost / (1 - SELL_FEE_PCT)
    take_profit_price = breakeven_price * (1 + NET_PROFIT_PCT)
    stop_loss_price = entry_price * (1 - SL_PCT)
    return breakeven_price, take_profit_price, stop_loss_price


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"position": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    price, err_detail = get_price()

    if price is None:
        send_telegram(
            f"⚠️ خطا: سرور وال‌گلد پاسخ نداد یا قیمت طلای ۱۸ عیار یافت نشد.\n"
            f"<code>{err_detail or 'جزئیات نامشخص'}</code>"
        )
        return

    # فیلتر امنیتی بازه قیمت منطقی
    if price < 20000000 or price > 35000000:
        send_telegram(f"⚠️ فیلتر امنیتی: قیمت دریافتی ({price:,.0f} تومان) خارج از بازه مجاز است.")
        return

    if TEST_MODE:
        be_sample, tp_sample, _ = calc_exit_levels(price)
        send_telegram(
            f"🔍 <b>تست موفقیت‌آمیز وال‌گلد</b>\n"
            f"💰 قیمت لحظه‌ای طلای ۱۸ عیار: <b>{price:,.0f}</b> تومان\n"
            f"⚖️ نقطه سر‌به‌سر فرضی (۱٪ کارمزد رفت و برگشت): <b>{be_sample:,.0f}</b> تومان\n"
            f"🎯 هدف فروش با ۱٪ سود خالص پس از سر‌به‌سر: <b>{tp_sample:,.0f}</b> تومان\n\n"
            f"<i>(حالت تست فعال است؛ سیگنال خرید/فروش ارسال نمی‌شود)</i>"
        )
        return

    state = load_state()
    pos = state.get("position")

    if pos:
        entry = float(pos["entry"])
        be_price, tp_price, sl_price = calc_exit_levels(entry)

        if price <= sl_price:
            send_telegram(
                f"🔴🔴 <b>STOP-LOSS فعال شد</b> 🔴🔴\n"
                f"قیمت فعلی: <b>{price:,.0f}</b> تومان\n"
                f"قیمت ورود: {entry:,.0f} تومان\n"
                f"حد ضرر: {sl_price:,.0f} تومان\n"
                f"⚡ سریع در اپ زرپین بفروشید!"
            )
            state["position"] = None
            save_state(state)

        elif price >= tp_price:
            send_telegram(
                f"🟢🟢 <b>TAKE-PROFIT (۱٪ سود قطعی پس از سر‌به‌سر) فعال شد</b> 🟢🟢\n"
                f"قیمت فعلی: <b>{price:,.0f}</b> تومان\n"
                f"قیمت ورود: {entry:,.0f} تومان\n"
                f"نقطه سر‌به‌سر: {be_price:,.0f} تومان\n"
                f"هدف سود: {tp_price:,.0f} تومان\n"
                f"⚡ سریع در اپ زرپین بفروشید!"
            )
            state["position"] = None
            save_state(state)
    else:
        if price >= BREAKOUT_PRICE:
            be_p, tp_p, sl_p = calc_exit_levels(price)
            send_telegram(
                f"🚀🚀 <b>سیگنال خرید (شکست مقاومت)</b> 🚀🚀\n"
                f"قیمت ورود: <b>{price:,.0f}</b> تومان\n"
                f"⚖️ سر‌به‌سر: {be_p:,.0f} تومان\n"
                f"🎯 هدف فروش: {tp_p:,.0f} تومان\n"
                f"🛑 حد ضرر: {sl_p:,.0f} تومان\n"
                f"⚡ سریع در اپ زرپین بخرید!"
            )
            state["position"] = {"entry": price}
            save_state(state)

        elif LOW_ZONE_MIN <= price <= LOW_ZONE_MAX:
            be_p, tp_p, sl_p = calc_exit_levels(price)
            send_telegram(
                f"🎣🎣 <b>سیگنال خرید (شکار کف)</b> 🎣🎣\n"
                f"قیمت ورود: <b>{price:,.0f}</b> تومان\n"
                f"⚖️ سر‌به‌سر: {be_p:,.0f} تومان\n"
                f"🎯 هدف فروش: {tp_p:,.0f} تومان\n"
                f"🛑 حد ضرر: {sl_p:,.0f} تومان\n"
                f"⚡ سریع در اپ زرپین بخرید!"
            )
            state["position"] = {"entry": price}
            save_state(state)


if __name__ == "__main__":
    main()
