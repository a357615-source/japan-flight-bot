import requests
import os
import json
from datetime import datetime

# ================= 🔧 環境設定區 =================
# ⚠️ 等正式 API 下放後，只需將此處改為 True
IS_PRODUCTION = False 
# ===============================================

# 專屬對照表
AIRLINE_NAMES = {"GK": "捷星日本 (GK)", "3K": "捷星亞洲 (3K)", "JQ": "捷星航空 (JQ)"}
AIRPORT_NAMES = {"TPE": "桃園", "NRT": "成田"}
AIRCRAFT_MODELS = {"320": "A320", "321": "A321", "32Q": "A321neo", "788": "B787-8"}

# 自動根據環境切換網址
BASE_URL = "https://api.amadeus.com" if IS_PRODUCTION else "https://test.api.amadeus.com"

def send_line_push(text_content):
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    if not token or not user_id: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": text_content}]}
    requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)

def get_amadeus_token():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    auth_url = f"{BASE_URL}/v1/security/oauth2/token"
    try:
        res = requests.post(auth_url, data={"grant_type": "client_credentials", "client_id": key, "client_secret": secret}, timeout=10)
        return res.json().get("access_token")
    except: return None

def check_flights():
    token = get_amadeus_token()
    if not token: return 

    # 監控日期組合 (2026年5月)
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    now_utc = datetime.utcnow()
    # 轉換成台北時間顯示用
    now_tpe_str = datetime.now().strftime("%H:%M")
    report = f"🚀【捷星監控 {now_tpe_str}】\n━━━━━━━━━━━━━━"
    found_any = False
    
    for dep, ret in date_pairs:
        url = f"{BASE_URL}/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE", "destinationLocationCode": "NRT",
            "departureDate": dep, "returnDate": ret, "adults": 1, 
            "includedAirlineCodes": "GK,3K", "nonStop": "false", "currencyCode": "TWD", "max": 1                         
        }
        try:
            res = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
            if "data" in res and len(res["data"]) > 0:
                flight = res["data"][0]
                price = int(float(flight["price"]["total"]))
                report += f"\n\n📅 {dep[5:]} → {ret[5:]}\n💰 TWD {price}\n━━━━━━━━━━━━━━"
                found_any = True
        except: continue

    # 判定是否發送訊息
    # 台北 23:30 = UTC 15:30，我們在 UTC 15:25~16:00 之間即便沒資料也會發通知報平安
    is_night_report = (now_utc.hour == 15 and 25 <= now_utc.minute <= 59)

    if found_any:
        send_line_push(report)
    elif is_night_report:
        env_status = "正式環境" if IS_PRODUCTION else "Sandbox (測試)"
        send_line_push(f"{report}\n\n🤖 系統提示：{env_status}未釋出數據\n✅ 網路與 API 連線正常")

if __name__ == "__main__":
    check_flights()
