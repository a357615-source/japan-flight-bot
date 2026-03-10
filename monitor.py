import requests
import os
import json
from datetime import datetime

# --- 專業設定區 ---
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
            print("💡 提醒：請確認您的手機已『加入好友』該機器人，否則 Push 會失敗。")
    except Exception as e:
        print(f"❌ LINE 請求異常: {e}")

def get_amadeus_token():
    """取得 Amadeus OAuth2 Token (測試環境專用)"""
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    
    # ⚠️ 重要：測試環境網址
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    
    try:
        print("正在取得 Sandbox Token...")
        res = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret
        }, timeout=10)
        
        if res.status_code != 200:
            print(f"❌ Token 取得失敗: {res.text}")
            return None
            
        print("✅ Sandbox Token 取得成功！")
        return res.json().get("access_token")
    except Exception as e:
        print(f"❌ Amadeus 連線異常: {e}")
        return None

def check_flights():
    token = get_amadeus_token()
    if not token:
        print("❌ 終止執行：無法取得有效 Token。請檢查 AMADEUS_KEY 是否為 Sandbox 版本。")
        return 

    # 測試日期的 8 組組合
    date_pairs = [
        ("2026-05-19", "2026-06-03"), ("2026-05-19", "2026-06-05"),
        ("2026-05-20", "2026-06-03"), ("2026-05-20", "2026-06-05"),
        ("2026-05-26", "2026-06-10"), ("2026-05-26", "2026-06-11"),
        ("2026-05-27", "2026-06-10"), ("2026-05-27", "2026-06-11")
    ]

    report = "🧪【Sandbox 測試模式 - 監控報表】\n"
    report += "----------------------------"
    
    found_any = False
    query_count = 0 
    
    print(f"開始在測試庫查詢 {len(date_pairs)} 組日期...")

    for dep, ret in date_pairs:
        # ⚠️ 重要：測試環境網址
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": "TPE", 
            "destinationLocationCode": "NRT",
            "departureDate": dep, 
            "returnDate": ret,
            "adults": 1, 
            "includedAirlineCodes": "GK,3K",
            "nonStop": "false", # 測試環境建議 false，增加抓到模擬資料的機率
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
                
                report += f"\n📅 {dep} ~ {ret}\n💰 模擬票價: TWD {price}\n⏰ 去:{dep_t} | 回:{ret_t}\n----------------------------"
                found_any = True
        except:
            continue

    # 額度預算
    monthly_usage = (query_count * 3 * 30)
    report += f"\n📊 測試額度預估: {monthly_usage} / {FREE_QUOTA_LIMIT}"

    if found_any:
        send_line_push(report)
    else:
        # 測試期間強制發送，確保您知道通道是通的
        send_line_push("🤖 測試連線成功！\n程式運作正常，但目前 Sandbox 模擬庫中沒有您設定的日期數據。")

if __name__ == "__main__":
    check_flights()
