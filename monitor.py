import requests
import os
from datetime import datetime

# --- 測試環境設定 ---
FREE_QUOTA_LIMIT = 2000 

def send_line_notification(message):
    token = os.getenv('LINE_TOKEN')
    if not token:
        print("❌ 錯誤: 找不到 LINE_TOKEN 變數")
        return
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    res = requests.post(url, headers=headers, data=data)
    print(f"📢 LINE 通知發送狀態: {res.status_code}")

def get_amadeus_token():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # ⚠️ 這裡使用 TEST 網址
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    try:
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        })
        token = res.json().get("access_token")
        if token:
            print("✅ 成功取得 Sandbox Token")
        return token
    except Exception as e:
        print(f"❌ Token 取得失敗: {e}")
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        send_line_notification("\n❌ 無法取得 Sandbox Token，請檢查 API Key。")
        return

    # 您的 8 組測試日期
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    report = "\n🧪【Sandbox 測試模式 - 機票監控】\n"
    report += "----------------------------"
    
    query_count = 0 
    found_any = False

    for dep, ret in date_pairs:
        # ⚠️ 這裡使用 TEST 網址
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE",
            "destinationLocationCode": "NRT",
            "departureDate": dep,
            "returnDate": ret,
            "adults": 1,
            "includedAirlineCodes": "GK,3K",
            "nonStop": "false",  # 測試環境改為 false 以增加搜尋機率
            "currencyCode": "TWD",
            "max": 1                         
        }
        
        try:
            query_count += 1
            response = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                flight = data["data"][0]
                price = int(float(flight["price"]["total"]))
                dep_time = flight["itineraries"][0]["segments"][0]["departure"]["at"][11:16]
                ret_time = flight["itineraries"][1]["segments"][0]["departure"]["at"][11:16]
                seats = flight.get("numberOfBookableSeats", "不明")

                report += f"\n📅 {dep} ~ {ret}"
                report += f"\n💰 模擬總價: TWD {price}"
                report += f"\n⏰ 去:{dep_time} | 回:{ret_time} | 💺:{seats}"
                report += "\n----------------------------"
                found_any = True
            else:
                print(f"ℹ️ 日期 {dep} 在測試庫中無數據")
        except Exception as e:
            print(f"⚠️ 查詢 {dep} 出錯: {e}")

    # 額度報告
    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 測試額度預估: 每月消耗 {monthly_usage}/{FREE_QUOTA_LIMIT}"

    if found_any:
        send_line_notification(report)
    else:
        send_line_notification("\n🧪 測試成功，但當前日期組合在 Sandbox 庫中無模擬票價。")

if __name__ == "__main__":
    check_flights()
