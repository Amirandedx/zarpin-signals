import os
import json
import requests
import re

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# --- تنظیمات نهایی ---
LOW_ZONE_MIN = 24300000   # شکار کف
LOW_ZONE_MAX = 24350000
BREAKOUT_PRICE = 24650000 # شکست مقاومت
SL_PCT = 0.015            # 1.5% استاپ لاس
TP_PCT = 0.03             # 3% تارگت

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

def get_price():
    try:
        url = "https://r.jina.ai/https://www.tgju.org/profile/gerami"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        if r.status_code == 200:
            # پیدا کردن تمام اعدادی که فرمت ۳ رقمی با کاما دارند (مثل 245,000,000)
            matches = re.findall(r'([0-9]{3},[0-9]{3},[0-9]{3})', r.text)
            for m in matches:
                price_rial = float(m.replace(",", ""))
                price_toman = price_rial / 10
                
                # --- فیلتر امنیتی (Sanity Check) ---
                # فقط اعدادی که بین ۲۰ تا ۳۰ میلیون تومان هستند، قیمت گرم ۱۸ عیار محسوب می‌شوند
                if 20000000 <= price_toman <= 30000000:
                    return price_toman
    except:
        pass
    return None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f: return json.load(f)
    return {"position": None}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f)

def main():
    price = get_price()
    
    # اگر قیمت پیدا نشد یا عددی خارج از محدوده بود (مثل قیمت سکه)، هیچ پیامی نمی‌فرستد
    if not price:
        return

    state = load_state()
    pos = state.get("position")

    # --- بررسی استاپ‌لاس و تارگت ---
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

    # --- بررسی سیگنال خرید ---
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
