import requests
import os
import json
from datetime import datetime, timedelta

# ================= 🔧 環境設定區 =================
IS_PRODUCTION = False 
# ===============================================

AIRLINE_NAMES = {"GK": "捷星日本 (GK)", "3K": "捷星亞洲 (3K)", "JQ": "捷星航空 (JQ)"}
AIRPORT_NAMES = {"TPE": "桃園", "NRT": "成田"}
AIRCRAFT_MODELS = {"320": "A320", "321": "A321", "32Q": "A321neo", "788": "B787-8"}

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

    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    # --- 修正時區顯示 (UTC 轉 台北 GMT+8) ---
    now_utc = datetime.utcnow()
    now_tpe = now_utc + timedelta(hours=8)
    now_tpe_str = now_tpe.strftime("%H:%M")

    report = f"🚀【捷星黃金時段監控 {now_tpe_str}】\n━━━━━━━━━━━━━━"
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
                
                # --- 重新加入消失的資料解析邏輯 ---
                dep_seg = flight["itineraries"][0]["segments"][0]
                ret_seg = flight["itineraries"][1]["segments"][0]
                
                carrier = AIRLINE_NAMES.get(dep_seg["carrierCode"], dep_seg["carrierCode"])
                flight_num = f"{dep_seg['carrierCode']}{dep_seg['number']}"
                origin = AIRPORT_NAMES.get(dep_seg["departure"]["iataCode"], dep_seg["departure"]["iataCode"])
                dest = AIRPORT_NAMES.get(dep_seg["arrival"]["iataCode"], dep_seg["arrival"]["iataCode"])
                dep_t = dep_seg["departure"]["at"][11:16]
                ret_t = ret_seg["departure"]["at"][11:16]
                aircraft = AIRCRAFT_MODELS.get(dep_seg["aircraft"]["code"], dep_seg["aircraft"]["code"])
                seats = flight.get("numberOfBookableSeats", "?")
                price = int(float(flight["price"]["total"]))
                
                # --- 重新加入精確版面 ---
                report += f"\n\n📅 {dep[5:]} → {ret[5:]}"
                report += f"\n✈️ {carrier} {flight_num}"
                report += f"\n🗺️ {origin} → {dest}"
                report += f"\n⏰ {dep_t} ｜ {ret_t}"
                report += f"\n🛸 {aircraft} ｜ 💺 {seats}"
                report += f"\n💰 TWD {price}"
                report += "\n━━━━━━━━━━━━━━"
                found_any = True
        except: continue

    # 判定是否發送訊息 (台北 23:30 區段)
    is_night_report = (now_tpe.hour == 23 and 30 <= now_tpe.minute <= 59)

    if found_any:
        send_line_push(report)
    elif is_night_report:
        env_status = "正式環境" if IS_PRODUCTION else "Sandbox (測試)"
        send_line_push(f"{report}\n\n🤖 系統提示：{env_status}未釋出數據\n✅ 網路連線正常")

if __name__ == "__main__":
    check_flights()
