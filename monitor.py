import requests
import os
from datetime import datetime

# 版本標籤：V2.0-PRO-FORMAT
FREE_QUOTA_LIMIT = 2000 

def send_line_notification(message):
    token = os.getenv('LINE_TOKEN')
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)

def get_amadeus_token():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # 目前仍使用 Sandbox 測試網址
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    res = requests.post(auth_url, data={
        "grant_type": "client_credentials",
        "client_id": key,
        "client_secret": secret
    })
    return res.json().get("access_token")

def check_flights():
    token = get_amadeus_token()
    
    # 組合您的 8 組監控日期
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    report = "\n🚀【捷星黃金時段 - 精準監控報表 V2】\n"
    report += "----------------------------"
    
    query_count = 0 
    for dep, ret in date_pairs:
        d1 = datetime.strptime(dep, "%Y-%m-%d")
        d2 = datetime.strptime(ret, "%Y-%m-%d")
        stay_days = (d2 - d1).days

        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE",
            "destinationLocationCode": "NRT",
            "departureDate": dep,
            "returnDate": ret,
            "adults": 1,
            "includedAirlineCodes": "GK,3K",
            "nonStop": "false", 
            "currencyCode": "TWD",
            "max": 1                         
        }
        
        try:
            query_count += 1
            response = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}).json()
            if "data" in response and len(response["data"]) > 0:
                flight = response["data"][0]
                price = int(float(flight["price"]["total"]))
                dep_time = flight["itineraries"][0]["segments"][0]["departure"]["at"][11:16]
                ret_time = flight["itineraries"][1]["segments"][0]["departure"]["at"][11:16]
                seats = flight.get("numberOfBookableSeats", "9")

                # 這是您要的精確格式內容
                report += f"\n📅 {dep} ~ {ret} ({stay_days}天)"
                report += f"\n💰 總價: TWD {price} (來回含稅)"
                report += f"\n⏰ 去程:{dep_time} | 回程:{ret_time}"
                report += f"\n💺 剩餘座位: {seats}"
                report += "\n----------------------------"
        except:
            continue

    # 額度計算
    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 額度預估: {monthly_usage} / {FREE_QUOTA_LIMIT}"
    
    send_line_notification(report)

if __name__ == "__main__":
    check_flights()
