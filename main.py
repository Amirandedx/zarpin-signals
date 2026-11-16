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

def get_usd_toman():
    # ۱. تلاش از صرافی نوبیتکس (بهترین منبع برای دلار آزاد)
    try:
        r = requests.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return float(data["lastTradePrice"]) / 10
    except:
        pass
    
    # ۲. تلاش از CoinGecko
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=irr", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "tether" in data and "irr" in data["tether"]:
                return float(data["tether"]["irr"]) / 10
    except:
        pass
        
    # ۳. قیمت پیش‌فرض (اگر اینترنت قطع بود، ربات کرش نکنه)
    return 60000.0

def get_gold_ounce_usd():
    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        if r.status_code == 200:
            return float(r.json()["price"])
    except:
        pass
    return 2400.0 # قیمت پیش‌فرض اونس

def main():
    send_telegram("⏳ در حال محاسبه قیمت طلا از منابع جهانی...")
    
    try:
        gold_oz_usd = get_gold_ounce_usd()
        usd_toman = get_usd_toman()
        
        # محاسبه: (اونس / ۳۱.۱) * عیار ۱۸ (۰.۷۵) * قیمت دلار
        gold_24k_gram_usd = gold_oz_usd / 31.1034768
        gold_18k_gram_usd = gold_24k_gram_usd * 0.75
        gold_18k_gram_toman = gold_18k_gram_usd * usd_toman
        
        msg = (
            f"✅ قیمت تخمینی طلای ۱۸ عیار (گرمی):\n"
            f"💰 {gold_18k_gram_toman:,.0f} تومان\n\n"
            f"🌍 اونس جهانی: ${gold_oz_usd:,.0f}\n"
            f"💵 دلار آزاد: {usd_toman:,.0f} تومان"
        )
        send_telegram(msg)
        
    except Exception as e:
        send_telegram(f"❌ خطا در محاسبه:\n{str(e)}")

if __name__ == "__main__":
    main()
