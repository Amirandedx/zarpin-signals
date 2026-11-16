import os
import requests

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

def get_gold_price():
    # استفاده از API رسمی TGJU برای طلای 18 عیار (گرمی)
    url = "https://api.tgju.org/v1/market/indicator/summary-table-data/gold_18k"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # استخراج قیمت از دیتای TGJU (قیمت به ریال است)
            price_str = data["current"][0]["value"]
            # حذف کاما از عدد (مثلا 245,000,000 میشه 245000000)
            clean_price = float(price_str.replace(",", ""))
            # تبدیل ریال به تومان (تقسیم بر 10)
            toman_price = clean_price / 10
            return toman_price
    except Exception as e:
        print(f"Error getting price: {e}")
    return None

def main():
    send_telegram("⏳ در حال دریافت قیمت طلا از TGJU...")
    price = get_gold_price()
    
    if price:
        # پیام تستی برای اینکه ببینیم قیمت درست اومده یا نه
        send_telegram(f"✅ قیمت طلای ۱۸ عیار (گرمی):\n💰 {price:,.0f} تومان")
    else:
        send_telegram("❌ متاسفانه در دریافت قیمت از TGJU خطایی رخ داد.")

if __name__ == "__main__":
    main()
