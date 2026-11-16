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

def main():
    send_telegram("⏳ در حال محاسبه قیمت طلا از منابع جهانی...")
    
    try:
        # ۱. گرفتن قیمت اونس جهانی طلا به دلار (از API گوگل)
        gold_url = "https://api.gold-api.com/price/XAU"
        gold_data = requests.get(gold_url, timeout=10).json()
        gold_oz_usd = float(gold_data["price"])
        
        # ۲. گرفتن قیمت دلار آزاد به ریال (از CoinGecko)
        usd_url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=irr"
        usd_data = requests.get(usd_url, timeout=10).json()
        usd_irr = float(usd_data["tether"]["irr"])
        
        # ۳. محاسبه قیمت طلای ۱۸ عیار (هر اونس = ۳۱.۱۰۳ گرم)
        # فرمول: (قیمت اونس / ۳۱.۱) * عیار (۰.۷۵) * قیمت دلار / ۱۰ (برای تومان)
        gold_24k_gram_irr = (gold_oz_usd / 31.1034768) * usd_irr
        gold_18k_gram_irr = gold_24k_gram_irr * 0.75
        gold_18k_gram_toman = gold_18k_gram_irr / 10
        
        msg = (
            f"✅ قیمت تخمینی طلای ۱۸ عیار (گرمی):\n"
            f"💰 {gold_18k_gram_toman:,.0f} تومان\n\n"
            f"🌍 اونس جهانی: ${gold_oz_usd:,.0f}\n"
            f"💵 دلار آزاد: {usd_irr:,.0f} ریال"
        )
        send_telegram(msg)
        
    except Exception as e:
        send_telegram(f"❌ خطا در محاسبه:\n{str(e)}")

if __name__ == "__main__":
    main()
