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
    urls = [
        "https://r.jina.ai/https://api-khazaneh.zarpin.com/v1/prc/prices/",
        "https://corsproxy.io/?url=https://api-khazaneh.zarpin.com/v1/prc/prices/",
        "https://api.allorigins.win/raw?url=https://api-khazaneh.zarpin.com/v1/prc/prices/"
    ]
    
    for u in urls:
        try:
            r = requests.get(u, timeout=20)
            if r.status_code == 200:
                text = r.text
                start = text.find('[')
                end = text.rfind(']') + 1
                if start != -1 and end != 0:
                    data = json.loads(text[start:end])
                    for item in data:
                        if item.get("code") == "GOLD_IRT":
                            return float(item["price"])
        except Exception:
            continue
    return None

def main():
    send_telegram("⏳ در حال تلاش برای دریافت قیمت از زرپین...")
    price = get_price()
    
    if price:
        send_telegram(f"✅ قیمت با موفقیت دریافت شد:\n💰 {price:,.0f} تومان")
    else:
        send_telegram("❌ متاسفانه هیچکدام از واسطه‌ها جواب ندادند.")

if __name__ == "__main__":
    main()
