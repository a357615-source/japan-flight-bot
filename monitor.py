import requests
import os
import json
from datetime import datetime

# --- 專業設定區 ---
# Amadeus 每月免費額度上限 (2000次)
FREE_QUOTA_LIMIT = 2000 

def send_line_push(text_content):
    """使用 LINE Messaging API 推送訊息"""
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.getenv('LINE_USER_ID')
    
    if not token or not user_id:
        print("❌ 偵錯：找不到 LINE 金鑰或 User ID，請檢查 GitHub Secrets 設定。")
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
        if res.status_code == 200:
            print(f"✅ LINE 訊息推播成功！")
        else:
            print(f"⚠️ LINE 推送失敗，狀態碼: {res.status_code}, 內容: {res.text}")
    except Exception as e:
        print(f"❌ LINE 請求異常: {e}")

def get_amadeus_token():
    """取得 Amadeus OAuth2 Token"""
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    
    # --- 關鍵切換：若使用 Sandbox 金鑰，請將 api 改成 test.api ---
    auth_url = "https://api.amadeus.com/v1/security/oauth2/token"
    
    try:
        print("正在取得 Amadeus Token...")
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        }, timeout=10)
        
        if res.status_code != 200:
            print(f"❌ Token 取得失敗: {res.text}")
            return None
            
        return res.json().get("access_token")
    except Exception as e:
        print(f"❌ Amadeus 連線異常: {e}")
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        print("❌ 終止執行：無法取得有效 Token，請確認 AMADEUS_KEY 是否正確。")
        return 

    # 您要求的 8 組 2026 年 5 月日期
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
    
    print(f"開始查詢 {len(date_pairs)} 組日期組合...")

    for dep, ret in date_pairs:
        d1 = datetime.strptime(dep, "%Y-%m-%d")
        d2 = datetime.strptime(ret, "%Y-%m-%d")
        stay_days = (d2 - d1).days

        # --- 關鍵切換：若使用 Sandbox 金鑰，請將 api 改成 test.api ---
        url = "https://api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE", 
            "destinationLocationCode": "NRT",
            "departureDate": dep, 
            "returnDate": ret,
            "adults": 1, 
            "includedAirlineCodes": "GK,3K",
            "nonStop": "true",
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
                seats = flight.get("numberOfBookableSeats", "不明")

                report += f"\n📅 {dep} ~ {ret} ({stay_days}天)"
                report += f"\n💰 總價: TWD {price} (來回含稅)"
                report += f"\n⏰ 去:{dep_t} | 回:{ret_t} | 💺:{seats}位"
                report += "\n----------------------------"
                found_any = True
            else:
                print(f"ℹ️ 日期 {dep} 查無捷星直飛航班。")
        except Exception as e:
            print(f"⚠️ 查詢日期 {dep} 時發生錯誤: {e}")
            continue

    # 額度計算
    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 額度預估: {monthly_usage} / {FREE_QUOTA_LIMIT}"
    report += f"\n狀態: {'✅ 安全' if monthly_usage < FREE_QUOTA_LIMIT else '⚠️ 警告'}"

    if found_any:
        send_line_push(report)
    else:
        # 強制發送測試訊息，確保您知道機器人有在跑
        send_line_push("🤖 監控報告：連線成功，但目前您設定的 8 組日期在捷星官網暫無直飛票價資訊。")

if __name__ == "__main__":
    check_flights()
