import os
import requests
import re

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
    send_telegram("⏳ در حال دریافت قیمت دقیق طلا از TGJU...")
    
    try:
        # استفاده از Jina AI برای خواندن سایت TGJU
        url = "https://r.jina.ai/https://www.tgju.org/profile/gerami"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=25)
        
        if r.status_code == 200:
            text = r.text
            # پیدا کردن الگوی قیمت (اعداد با کاما مثل 3,450,000)
            matches = re.findall(r'([1-9]\d{0,2}(?:,\d{3})+)', text)
            
            if matches:
                # معمولاً اولین عدد بزرگ در صفحه، قیمت فعلی گرمی ۱۸ عیار است
                price_str = matches[0]
                price_rial = float(price_str.replace(",", ""))
                price_toman = price_rial / 10  # تبدیل ریال به تومان
                
                send_telegram(f"✅ قیمت طلای ۱۸ عیار (گرمی):\n💰 {price_toman:,.0f} تومان")
                return
            
            send_telegram("❌ قیمت در متن پیدا نشد.")
        else:
            send_telegram(f"❌ خطای سرور: {r.status_code}")
            
    except Exception as e:
        send_telegram(f"❌ خطا: {str(e)}")

if __name__ == "__main__":
    main()
