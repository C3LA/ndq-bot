from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔐 Your IG login tokens
API_KEY = '1cc8abc22deb15de4f620c6733696db4df1786f5'
ACCOUNT_ID = 'FWM4O'
CST = 'd7837dcede074923894ff08ff80afdbf5488e80ca5170b6ed788fec92999f8CC01113'
X_SECURITY_TOKEN = 'c59659f2fa16eeebf0edd85e217126dca1336158f5ad0d57307d2fd1c9d8eeCD01112'
API_URL = 'https://api.ig.com/gateway/deal'

@app.route('/webhook', methods=['POST'])
def webhook():
    import json
    data = json.loads(request.data)
    print("[📡] Webhook received:", data)

    direction = data.get("direction")
    epic = data.get("epic")
    size = data.get("size", 1)
    stop_distance = data.get("sl", 20)
    limit_distance = data.get("tp", 30)

    if not all([direction, epic]):
        return jsonify({"error": "Missing fields"}), 400

    order_payload = {
        "epic": epic,
        "expiry": "-",
        "direction": direction.upper(),
        "size": size,
        "orderType": "MARKET",
        "guaranteedStop": False,
        "stopDistance": stop_distance,
        "limitDistance": limit_distance,
        "forceOpen": True,
        "currencyCode": "GBP",
        "dealReference": "tv-auto-trade"
    }

    headers = {
        "X-IG-API-KEY": API_KEY,
        "CST": CST,
        "X-SECURITY-TOKEN": X_SECURITY_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2"
    }

    response = requests.post(f"{API_URL}/positions/otc", json=order_payload, headers=headers)

    if response.status_code == 200:
        print("[✅] Trade placed.")
        return jsonify({"status": "Trade placed", "response": response.json()})
    else:
        print("[❌] Failed to place trade:", response.text)
        return jsonify({"status": "Trade failed", "error": response.text}), 400
   

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Use Render's port if available
    app.run(host='0.0.0.0', port=port)