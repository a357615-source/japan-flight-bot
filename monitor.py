import requests
import os
import json
from datetime import datetime

# --- 專業對照表 (確保顯示中文名稱) ---
AIRLINE_NAMES = {"GK": "捷星日本 (GK)", "3K": "捷星亞洲 (3K)", "JQ": "捷星航空 (JQ)"}
AIRPORT_NAMES = {"TPE": "台北桃園", "NRT": "東京成田", "HND": "東京羽田", "KIX": "大阪關西"}
AIRCRAFT_MODELS = {"320": "A320", "321": "A321", "32Q": "A321neo", "788": "B787-8"}
FREE_QUOTA_LIMIT = 2000 

def send_line_push(text_content):
    """使用 LINE Messaging API 推送格式化報表"""
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    if not token or not user_id:
        print("❌ 錯誤：找不到 LINE 金鑰或 User ID")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": text_content}]}
    
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if res.status_code == 200:
            print("✅ LINE 報表推播成功！")
        else:
            print(f"⚠️ LINE 推送失敗: {res.text}")
    except Exception as e:
        print(f"❌ LINE 連線異常: {e}")

def get_amadeus_token():
    """取得 Amadeus Sandbox Token"""
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # ⚠️ 目前使用 Sandbox 測試網址
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    try:
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        }, timeout=10)
        return res.json().get("access_token")
    except:
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        print("❌ 無法取得 Amadeus Token")
        return 

    # 監控的 8 組日期組合
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    now_str = datetime.now().strftime("%H:%M")
    report = f"🚀【捷星黃金時段 - 精準報表 {now_str}】\n"
    report += "----------------------------"
    
    found_any = False
    query_count = 0
    
    for dep, ret in date_pairs:
        # ⚠️ 目前使用 Sandbox 測試網址
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
                
                # 機場、航空、機型解析
                origin = AIRPORT_NAMES.get(dep_seg["departure"]["iataCode"], dep_seg["departure"]["iataCode"])
                dest = AIRPORT_NAMES.get(dep_seg["arrival"]["iataCode"], dep_seg["arrival"]["iataCode"])
                carrier = AIRLINE_NAMES.get(dep_seg["carrierCode"], dep_seg["carrierCode"])
                flight_num = f"{dep_seg['carrierCode']}{dep_seg['number']}"
                aircraft = AIRCRAFT_MODELS.get(dep_seg["aircraft"]["code"], dep_seg["aircraft"]["code"])
                
                price = int(float(flight["price"]["total"]))
                dep_t = dep_seg["departure"]["at"][11:16]
                ret_t = ret_seg["departure"]["at"][11:16]
                seats = flight.get("numberOfBookableSeats", "?")

                # 按照您要求的精確格式輸出
                report += f"\n📅 {dep} ~ {ret}"
                report += f"\n🗺️ 航線: {origin} ✈️ {dest}"
                report += f"\n✈️ 航班: {carrier} {flight_num}"
                report += f"\n🛸 機型: {aircraft} | 💺 剩餘: {seats}位"
                report += f"\n💰 總價: TWD {price} (來回含稅)"
                report += f"\n⏰ 去:{dep_t} | 回:{ret_t}"
                report += "\n----------------------------"
                found_any = True
        except: continue

    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 額度預估: {monthly_usage} / {FREE_QUOTA_LIMIT}"

    if found_any:
        send_line_push(report)
    else:
        send_line_push("🤖 測試成功：連線正常，但目前 Sandbox 庫中無捷星 2026 年 5 月數據。")

if __name__ == "__main__":
    check_flights()
