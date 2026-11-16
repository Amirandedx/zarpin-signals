import os
import requests
import json

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def main():
    send_telegram("⏳ در حال تلاش برای دریافت قیمت از زرپین...")
    
    # استفاده از یک واسطه جدید
    url = "https://api.codetabs.com/v1/proxy?quest=https://api-khazaneh.zarpin.com/v1/prc/prices/"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                if item.get("code") == "GOLD_IRT":
                    price = float(item["price"])
                    send_telegram(f"✅ قیمت با موفقیت دریافت شد:\n💰 {price:,.0f} تومان")
                    return
            send_telegram("❌ قیمت پیدا نشد (کد GOLD_IRT در پاسخ نبود)")
        else:
            send_telegram(f"❌ خطای سرور زرپین: {r.status_code}")
    except Exception as e:
        send_telegram(f"❌ خطا در اتصال: {str(e)}")

if __name__ == "__main__":
    main()
