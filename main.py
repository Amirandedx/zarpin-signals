import os
import requests
from datetime import datetime

# --- تنظیمات ---
# این‌ها رو بعداً در گیت‌هاب تنظیم می‌کنیم، فعلاً دست نزن
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- قیمت ---
def get_gold_price():
    # لیستی از ۳ واسطه مختلف برای دریافت قیمت
    proxy_urls = [
        "https://api.codetabs.com/v1/proxy?quest=https://api-khazaneh.zarpin.com/v1/prc/prices/",
        "https://api.allorigins.win/raw?url=https://api-khazaneh.zarpin.com/v1/prc/prices/",
        "https://corsproxy.io/?https://api-khazaneh.zarpin.com/v1/prc/prices/"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # امتحان کردن واسطه‌ها یکی یکی
    for url in proxy_urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json() 
                for item in data:
                    if item.get("code") == "GOLD_IRT":
                        print(f"Price found successfully!")
                        return float(item["price"])
        except Exception:
            continue # اگر این واسطه خراب بود، میره سراغ واسطه بعدی
            
    print("Error: همه واسطه‌ها خراب بودند.")
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
    send_telegram("🔔 <b>تست موفقیت‌آمیز!</b>\nاتصال ربات به تلگرام برقرار شد. 🎉")
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
