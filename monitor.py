import requests
import os
import json
from datetime import datetime

# --- 專業設定區 ---
FREE_QUOTA_LIMIT = 2000  # Amadeus 每月免費額度

def send_line_push(text_content):
    """使用 LINE Messaging API 發送主動推送訊息"""
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    
    if not token or not user_id:
        print("❌ 錯誤：找不到 LINE 金鑰或 User ID，請檢查 Secrets 設定。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text_content}]
    }
    
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        res.raise_for_status()
        print(f"✅ LINE 訊息推播成功！")
    except Exception as e:
        print(f"❌ LINE 發送失敗: {e}")

def get_amadeus_token():
    """取得 Amadeus OAuth2 Token (正式生產環境網址)"""
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    # 若要測試請在網址前加 test.，正式上線請維持 api.amadeus.com
    auth_url = "https://api.amadeus.com/v1/security/oauth2/token"
    try:
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        }, timeout=10)
        return res.json().get("access_token")
    except Exception as e:
        print(f"❌ 無法取得 Amadeus Token: {e}")
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        return 

    # 您指定的 8 組監控日期 (5/19, 20, 26, 27 出發)
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    report = "🚀【捷星黃金時段 - 精準監控報表】\n"
    report += "----------------------------"
    
    found_any = False
    query_count = 0 
    
    for dep, ret in date_pairs:
        d1 = datetime.strptime(dep, "%Y-%m-%d")
        d2 = datetime.strptime(ret, "%Y-%m-%d")
        stay_days = (d2 - d1).days

        # Amadeus 查詢網址 (正式環境)
        url = "https://api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE", 
            "destinationLocationCode": "NRT",
            "departureDate": dep, 
            "returnDate": ret,
            "adults": 1, 
            "includedAirlineCodes": "GK,3K", # 鎖定捷星
            "nonStop": "true",               # 強制直飛
            "currencyCode": "TWD", 
            "max": 1                         
        }
        
        try:
            query_count += 1
            res = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
            
            if "data" in res and len(res["data"]) > 0:
                flight = res["data"][0]
                price = int(float(flight["price"]["total"]))
                dep_t = flight["itineraries"][0]["segments"][0]["departure"]["at"][11:16]
                ret_t = flight["itineraries"][1]["segments"][0]["departure"]["at"][11:16]
                seats = flight.get("numberOfBookableSeats", "9+")

                report += f"\n📅 {dep} ~ {ret} ({stay_days}天)"
                report += f"\n💰 總價: TWD {price} (來回含稅)"
                report += f"\n⏰ 去:{dep_t} | 回:{ret_t} | 💺:{seats}位"
                report += "\n----------------------------"
                found_any = True
        except Exception as e:
            print(f"⚠️ 日期 {dep} 查詢異常: {e}")
            continue

    # 額度計算 (8次 * 3時段 * 30天)
    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 額度預估: {monthly_usage} / {FREE_QUOTA_LIMIT}"
    report += f"\n狀態: {'✅ 安全' if monthly_usage < FREE_QUOTA_LIMIT else '⚠️ 接近上限'}"

    if found_any:
        send_line_push(report)
    else:
        # 測試期間若完全沒票也發通知確認機器人活著，上線後可註解掉
        send_line_push("🤖 監控報告：目前指定的 8 組日期暫無直飛航班資訊。")

if __name__ == "__main__":
    check_flights()
