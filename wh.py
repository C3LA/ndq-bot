from flask import Flask, request, jsonify
import requests
import json
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
    print("[👋] Webhook function entered!", flush=True)

    try:
        # Log raw body
        raw = request.get_data(as_text=True)
        print("[📡] Raw data:", raw, flush=True)

        # Parse JSON safely
        try:
            data = json.loads(raw)
        except Exception as e:
            print("[❌] Failed to parse JSON:", str(e), flush=True)
            return jsonify({"error": "Invalid JSON"}), 400

        print("[📡] Parsed JSON:", data, flush=True)

        # Extract values
        direction = data.get("direction")
        epic = data.get("epic")
        size = data.get("size", 1)
        stop_distance = data.get("sl", 20)
        limit_distance = data.get("tp", 30)

        if not all([direction, epic]):
            print("[❌] Missing 'direction' or 'epic'", flush=True)
            return jsonify({"error": "Missing fields"}), 400

def login_to_ig():
    login_url = f"{API_URL}/session"
    payload = {
        "identifier": "CalebFish",
        "password": "Facetime1977"
    }
    headers = {
        "X-IG-API-KEY": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2"
    }
    response = requests.post(login_url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception("IG login failed: " + response.text)

    cst = response.headers["CST"]
    xst = response.headers["X-SECURITY-TOKEN"]
    print("[🔐] IG login successful", flush=True)
    return cst, xst

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

        CST, X_SECURITY_TOKEN = login_to_ig()
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
            print("[✅] Trade placed successfully!", flush=True)
            return jsonify({"status": "Trade placed", "response": response.json()})
        else:
            print("[❌] Trade failed:", response.text, flush=True)
            return jsonify({"status": "Trade failed", "error": response.text}), 400

    except Exception as e:
        print("[❌] Unhandled error:", str(e), flush=True)
        return jsonify({"error": "Unhandled exception"}), 500

@app.route('/ping')
def ping():
    print("[👋] Ping route hit!", flush=True)
    return "pong", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
