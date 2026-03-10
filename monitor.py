import requests
import os

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"
    }
    payload = {
        "to": os.getenv('LINE_USER_ID'),
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, json=payload)

def check_flights():
    key = os.getenv('AMADEUS_KEY')
    secret = os.getenv('AMADEUS_SECRET')
    
    # 換取 Token
    auth_res = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token", 
                             data={"grant_type": "client_credentials", "client_id": key, "client_secret": secret})
    token = auth_res.json().get("access_token")

    # 查機票 (台北 TPE -> 東京 NRT)
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {"originLocationCode": "TPE", "destinationLocationCode": "NRT", 
              "departureDate": "2026-07-01", "adults": 1, "currencyCode": "TWD", "max": 1}
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, params=params, headers=headers).json()

    if "data" in res and len(res["data"]) > 0:
        price = res["data"][0]["price"]["total"]
        send_line(f"✈️ 2026/07/01 日本機票監控回報：\n目前最低價：TWD {price}\n(資料來自 Amadeus 測試環境)")
    else:
        send_line("目前查無機票資料，請檢查日期或稍後再試。")

if __name__ == "__main__":
    check_flights()
