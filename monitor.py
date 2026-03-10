import requests
import os
import json
from datetime import datetime

# --- 專屬對照表 (僅保留桃園、成田) ---
AIRLINE_NAMES = {"GK": "捷星日本 (GK)", "3K": "捷星亞洲 (3K)", "JQ": "捷星航空 (JQ)"}
AIRPORT_NAMES = {"TPE": "桃園", "NRT": "成田"}
AIRCRAFT_MODELS = {"320": "A320", "321": "A321", "32Q": "A321neo", "788": "B787-8"}
FREE_QUOTA_LIMIT = 2000 

def send_line_push(text_content):
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    if not token or not user_id: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": text_content}]}
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        print(f"✅ LINE 發送狀態: {res.status_code}")
    except: print("❌ LINE 發送失敗")

def get_amadeus_token():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # ⚠️ 目前為 Sandbox 環境，正式金鑰請移除 'test.'
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
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

    now_str = datetime.now().strftime("%H:%M")
    report = f"🚀【捷星黃金時段監控 {now_str}】\n"
    report += "━━━━━━━━━━━━━━"
    
    found_any = False
    query_count = 0
    
    for dep, ret in date_pairs:
        # ⚠️ 目前為 Sandbox 環境
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE", "destinationLocationCode": "NRT",
            "departureDate": dep, "returnDate": ret, "adults": 1, 
            "includedAirlineCodes": "GK,3K", "nonStop": "false", "currencyCode": "TWD", "max": 1                         
        }
        
        try:
            query_count += 1
            res = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
            if "data" in res and len(res["data"]) > 0:
                flight = res["data"][0]
                dep_seg = flight["itineraries"][0]["segments"][0]
                ret_seg = flight["itineraries"][1]["segments"][0]
                
                # 資料擷取與轉換
                dep_short, ret_short = dep[5:], ret[5:]
                origin = AIRPORT_NAMES.get(dep_seg["departure"]["iataCode"], dep_seg["departure"]["iataCode"])
                dest = AIRPORT_NAMES.get(dep_seg["arrival"]["iataCode"], dep_seg["arrival"]["iataCode"])
                carrier = AIRLINE_NAMES.get(dep_seg["carrierCode"], dep_seg["carrierCode"])
                flight_num = f"{dep_seg['carrierCode']}{dep_seg['number']}"
                aircraft = AIRCRAFT_MODELS.get(dep_seg["aircraft"]["code"], dep_seg["aircraft"]["code"])
                price = int(float(flight["price"]["total"]))
                dep_t = dep_seg["departure"]["at"][11:16]
                ret_t = ret_seg["departure"]["at"][11:16]
                seats = flight.get("numberOfBookableSeats", "?")

                # --- 您要求的精確版面 ---
                report += f"\n\n📅 {dep_short} → {ret_short}"
                report += f"\n✈️ {carrier} {flight_num}"
                report += f"\n🗺️ {origin} → {dest}"
                report += f"\n⏰ {dep_t} ｜ {ret_t}"
                report += f"\n🛸 {aircraft} ｜ 💺 {seats}"
                report += f"\n💰 TWD {price}"
                report += "\n\n━━━━━━━━━━━━━━"
                found_any = True
        except: continue

    monthly_usage = (query_count * 3 * 30)
    report += f"\n\n📊 API 使用預估\n{monthly_usage} / {FREE_QUOTA_LIMIT}"

    if found_any:
        send_line_push(report)
    else:
        # 測試訊息也同步版面格式
        test_msg = f"🚀【捷星黃金時段監控 {now_str}】\n━━━━━━━━━━━━━━\n\n🤖 測試成功：連線正常，但目前 Sandbox 庫中無 2026 年數據。\n\n━━━━━━━━━━━━━━\n\n📊 API 使用預估\n{monthly_usage} / {FREE_QUOTA_LIMIT}"
        send_line_push(test_msg)

if __name__ == "__main__":
    check_flights()
