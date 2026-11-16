import os
import requests
from datetime import datetime

# --- تنظیمات ---
# این‌ها رو بعداً در گیت‌هاب تنظیم می‌کنیم، فعلاً دست نزن
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- قیمت ---
def get_gold_price():
    url = "https://api-khazaneh.zarpin.com/v1/prc/prices/"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        for item in r.json():
            if item["code"] == "GOLD_IRT":
                return float(item["price"])
    except Exception as e:
        print(f"Error getting price: {e}")
    return None

# --- ارسال پیام ---
def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram config missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending telegram: {e}")

# --- منطق سیگنال ---
def main():
    price = get_gold_price()
    if price is None:
        return
    
    print(f"Price: {price}")

    # مثال ساده: اگر قیمت از 24,850,000 بیشتر بود، پیام بفرست
    # (برای تست کردن، این عدد رو عوض کن)
    if price > 24_850_000:
        message = (
            f"🚨 <b>سیگنال خرید (تستی)</b> 🚨\n"
            f"قیمت به {price:,.0f} رسید!\n"
            f"⏰ {datetime.now():%H:%M}"
        )
        send_telegram(message)
        print("Signal sent!")

if __name__ == "__main__":
    main()
