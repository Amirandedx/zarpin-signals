import os
import json
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# --- حالت تست ---
# این خط را فعلا True بگذار تا فقط قیمت را بفرستد و سیگنال خرید/فروش ندهد!
TEST_MODE = True 

# --- تنظیمات ---
LOW_ZONE_MIN = 24300000
LOW_ZONE_MAX = 24350000
BREAKOUT_PRICE = 24650000
SL_PCT = 0.015
TP_PCT = 0.03

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

def get_price():
    # خواندن دقیق از API خود زرپین با استفاده از ۳ پروکسی مختلف
    target_url = "https://api-khazaneh.zarpin.com/v1/prc/prices/"
    proxies = [
        f"https://api.allorigins.win/raw?url={target_url}",
        f"https://api.codetabs.com/v1/proxy?quest={target_url}",
        f"https://corsproxy.io/?{target_url}"
    ]
    
    for proxy in proxies:
        try:
            r = requests.get(proxy, timeout=15)
            if r.status_code == 200:
                data = r.json()
                # پیدا کردن دقیق GOLD_IRT از پاسخ زرپین
                for item in data:
                    if item.get("code") == "GOLD_IRT":
                        return float(item["price"]) / 10  # تبدیل ریال به تومان
        except:
            continue
    return None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f: return json.load(f)
    return {"position": None}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f)

def main():
    price = get_price()
    
    if not price:
        send_telegram("⚠️ خطا: سرورهای زرپین پاسخ ندادند. (هیچ سیگنالی صادر نشد)")
        return

    # فیلتر امنیتی: اگر قیمت خارج از محدوده عقلانی بود، نادیده بگیر
    if price < 20000000 or price > 30000000:
        send_telegram(f"⚠️ فیلتر امنیتی: قیمت دریافتی ({price:,.0f}) غیرمنطقی است.")
        return

    # اگر حالت تست روشن باشد، فقط قیمت را می‌فرستد و کاری نمی‌کند
    if TEST_MODE:
        send_telegram(f"🔍 تست موفق: قیمت دقیق زرپین دریافت شد:\n💰 {price:,.0f} تومان")
        return

    # --- منطق اصلی (فعلا غیرفعال است چون TEST_MODE=True است) ---
    state = load_state()
    pos = state.get("position")

    if pos:
        entry = pos["entry"]
        sl = entry * (1 - SL_PCT)
        tp = entry * (1 + TP_PCT)
        
        if price <= sl:
            send_telegram(f"🔴🔴 <b>STOP-LOSS فعال شد</b> 🔴🔴\nقیمت: {price:,.0f}\nEntry: {entry:,.0f}\n⚡ سریع در اپ زرپین بفروش!")
            state["position"] = None
            save_state(state)
        elif price >= tp:
            send_telegram(f"🟢🟢 <b>TAKE-PROFIT فعال شد</b> 🟢🟢\nقیمت: {price:,.0f}\nEntry: {entry:,.0f}\n⚡ سریع در اپ زرپین بفروش!")
            state["position"] = None
            save_state(state)
    else:
        if price >= BREAKOUT_PRICE:
            send_telegram(f"🚀🚀 <b>سیگنال خرید (شکست مقاومت)</b> 🚀🚀\nقیمت: {price:,.0f}\n⚡ سریع در اپ زرپین بخر!")
            state["position"] = {"entry": price}
            save_state(state)
        elif LOW_ZONE_MIN <= price <= LOW_ZONE_MAX:
            send_telegram(f"🎣🎣 <b>سیگنال خرید (شکار کف)</b> 🎣🎣\nقیمت: {price:,.0f}\n⚡ سریع در اپ زرپین بخر!")
            state["position"] = {"entry": price}
            save_state(state)

if __name__ == "__main__":
    main()
