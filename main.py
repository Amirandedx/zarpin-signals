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

def get_price():
    # تلاش اول: پروکسی برای گرفتن از خود زرپین
    proxy_url = "https://api.cors.lol/?url=https://api-khazaneh.zarpin.com/v1/prc/prices/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        r = requests.get(proxy_url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                if item.get("code") == "GOLD_IRT":
                    return float(item["price"]), "زرپین"
    except Exception:
        pass # اگر نشد میره سراغ روش دوم

    # تلاش دوم: گرفتن قیمت از TGJU (مرجع قیمت طلا)
    try:
        tgju_url = "https://call1.tgju.org/ajax.json"
        r = requests.get(tgju_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # در سایت TGJU، کلید gerami مربوط به طلای 18 عیار است
            price_str = data['current']['gerami']['p'] # مثل "45,200,000"
            price = float(price_str.replace(',', ''))
            return price, "TGJU (جایگزین)"
    except Exception as e:
        print(f"TGJU Error: {e}")

    return None, "هیچ منبعی پاسخ نداد"

def main():
    send_telegram("⏳ در حال تلاش برای دریافت قیمت...")
    price, source = get_price()
    
    if price:
        send_telegram(f"✅ قیمت با موفقیت دریافت شد (از {source}):\n💰 {price:,.0f} تومان")
    else:
        send_telegram("❌ متاسفانه هیچ منبعی پاسخ نداد. لطفا بعدا تلاش کنید.")

if __name__ == "__main__":
    main()
