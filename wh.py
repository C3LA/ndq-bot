from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# 🔐 IG API Setup
API_KEY = '1cc8abc22deb15de4f620c6733696db4df1786f5'
ACCOUNT_ID = 'FWM4O'
API_URL = 'https://api.ig.com/gateway/deal'

# 🔐 Your IG credentials
IG_USERNAME = 'CalebFish'
IG_PASSWORD = 'Facetime1977!'

# 🔁 IG Login Function
def login_to_ig():
    login_url = f"{API_URL}/session"
    payload = {
        "identifier": IG_USERNAME,
        "password": IG_PASSWORD
    }
    headers = {
        "X-IG-API-KEY": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2"
    }

    response = requests.post(login_url, json=payload, headers=headers)
    if response.status_code == 200:
    print("[✅] Trade placed successfully!", flush=True)
    print("[📝] Full IG response:", response.json(), flush=True)
    return jsonify({"status": "Trade placed", "response": response.json()})

    cst = response.headers["CST"]
    xst = response.headers["X-SECURITY-TOKEN"]
    print("[🔐] IG login successful", flush=True)
    return cst, xst

@app.route('/webhook', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def webhook():
    print("[👋] Webhook function entered!", flush=True)

    try:
        raw = request.get_data(as_text=True)
        print("[📡] Raw data:", raw, flush=True)

        try:
            data = json.loads(raw)
        except Exception as e:
            print("[❌] Failed to parse JSON:", str(e), flush=True)
            return jsonify({"error": "Unhandled exception"}), 500
        print("[📡] Parsed JSON:", data, flush=True)

        direction = data.get("direction")
        epic = data.get("epic")
        size = data.get("size", 1)
        stop_distance = data.get("sl", 20)
        limit_distance = data.get("tp", 30)

        if not all([direction, epic]):
            print("[❌] Missing 'direction' or 'epic'", flush=True)
            return jsonify({"error": "Missing fields"}), 400

        # Tokens
        CST, X_SECURITY_TOKEN = login_to_ig()

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
            print("[✅] Trade placed successfully!", flush=True)
            return jsonify({"status": "Trade placed", "response": response.json()})
        else:
            print("[❌] Trade failed:", response.text, flush=True)
            return jsonify({"status": "Trade failed", "error": response.text}), 400

        # 🔒 This guarantees the route always ends with a valid response
        return jsonify({"status": "received"}), 200

    except Exception as e:
        print("[❌] Unhandled error:", str(e), flush=True)
        return jsonify({"error": "Unhandled exception"}), 500


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
