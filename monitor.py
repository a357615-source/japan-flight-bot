import requests
import os
from datetime import datetime

# --- 專業設定區 ---
FREE_QUOTA_LIMIT = 2000  # Amadeus 每月免費額度上限

def send_line_notification(message):
    token = os.getenv('LINE_TOKEN')
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)

def get_amadeus_token():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # 生產環境 Token 網址 (簽署合約後專用)
    auth_url = "https://api.amadeus.com/v1/security/oauth2/token"
    try:
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        })
        return res.json().get("access_token")
    except:
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        print("Error: 無法取得 Production Token。請檢查 GitHub Secrets 中的金鑰。")
        return

    # 依照您要求更新的 8 組精確去回日期 (滯留 10 天以上)
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    report = "\n🚀【捷星黃金時段 - 精準監控報表】\n"
    report += "----------------------------"
    
    query_count = 0 
    found_any = False

    for dep, ret in date_pairs:
        d1 = datetime.strptime(dep, "%Y-%m-%d")
        d2 = datetime.strptime(ret, "%Y-%m-%d")
        stay_days = (d2 - d1).days

        # 正式環境查詢網址
        url = "https://api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE",
            "destinationLocationCode": "NRT",
            "departureDate": dep,
            "returnDate": ret,
            "adults": 1,
            "includedAirlineCodes": "GK,3K", # 指定捷星
            "nonStop": "true",               # 強制直飛
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

                report += f"\n📅 {dep} ~ {ret} ({stay_days}天)"
                report += f"\n💰 總價: TWD {price} (來回含稅)"
                report += f"\n⏰ 去:{dep_time} | 回:{ret_time} | 💺:{seats}位"
                report += "\n----------------------------"
                found_any = True
        except:
            continue

    # --- 額度計算區 ---
    # 每天跑 3 次，一個月 30 天的預估
    monthly_usage = (query_count * 3 * 30)
    remaining = FREE_QUOTA_LIMIT - monthly_usage
    
    report += f"\n📊 額度報告：每月預估消耗 {monthly_usage}/{FREE_QUOTA_LIMIT}"
    report += f"\n安全狀態: {'✅ 正常' if remaining > 0 else '⚠️ 警告'}"

    if found_any:
        send_line_notification(report)

if __name__ == "__main__":
    check_flights()
