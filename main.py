import os
import json
import requests
from datetime import datetime

# --- تنظیمات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_gold_price():
    # استفاده از سرویس Jina AI برای دور زدن محدودیت IP
    url = "https://r.jina.ai/https://api-khazaneh.zarpin.com/v1/prc/prices/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            text = r.text
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                data = json.loads(json_str)
                for item in data:
                    if item.get("code") == "GOLD_IRT":
                        print("Price found successfully!")
                        return float(item["price"])
    except Exception as e:
        print(f"Error getting price: {e}")
    
    print("Error: could not get price.")
    return None

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

def main():
    # پیام تست
    send_telegram("🔔 <b>تست موفقیت‌آمیز!</b>\nاتصال ربات به تلگرام برقرار شد. 🎉")
    
    price = get_gold_price()
    if price is None:
        return
        
    print(f"Price: {price}")

    # اگر قیمت بیشتر از 24,850,000 بود، سیگنال خرید بفرست (تستی)
    if price > 24850000:
        message = f"🚨 <b>سیگنال خرید (تستی)</b> 🚨\nقیمت به {price:,.0f} رسید!\n⏰ {datetime.now():%H:%M}"
        send_telegram(message)
        print("Signal sent!")

if __name__ == "__main__":
    main()
