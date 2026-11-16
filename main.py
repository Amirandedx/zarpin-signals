import os
import json
import requests
import re

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# --- تنظیمات نهایی بر اساس چارت زرپین و داریک ---
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
    # فقط و فقط از TGJU می‌خوانیم. هیچ حدس و محاسبه‌ای در کار نیست.
    try:
        url = "https://r.jina.ai/https://www.tgju.org/profile/gerami"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        if r.status_code == 200:
            # پیدا کردن تمام اعداد فرمت‌شده (مثل 245,674,000)
            matches = re.findall(r'([0-9]{2,3},[0-9]{3},[0-9]{3})', r.text)
            for m in matches:
                val = float(m.replace(",", ""))
                # اگر عدد بین ۲۰۰ تا ۳۰۰ میلیون ریال (۲۰ تا ۳۰ میلیون تومان) بود، یعنی قیمت گرمی ۱۸ عیار است
                if 200000000 <= val <= 300000000:
                    return val / 10
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
    
    # اگر سایت TGJU قطع بود، هیچ عدد اشتباهی نمی‌فرستیم
    if not price:
        send_telegram("⚠️ خطا در ارتباط با TGJU. لطفا بعدا بررسی کنید.")
        return

    state = load_state()
    pos = state.get("position")

    # --- بررسی استاپ‌لاس و تارگت (اگر قبلا خرید کرده باشیم) ---
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

    # --- بررسی سیگنال خرید (اگر پوزیشن باز نداریم) ---
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
