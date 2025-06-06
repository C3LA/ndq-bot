from flask import Flask, request, jsonify
import requests
import json
import os
import csv
from datetime import datetime

app = Flask(__name__)

# ===🔐 IG Credentials ===
API_KEY = 'your_api_key'
USERNAME = 'your_ig_username'
PASSWORD = 'your_ig_password'
ACCOUNT_ID = 'your_account_id'
API_URL = 'https://api.ig.com/gateway/deal'

# ===🔧 Config ===
MAX_TRADES_PER_DAY = 5
TRADE_HOURS = (9, 30, 17, 0)  # (start_hour, start_minute, end_hour, end_minute)
STRATEGY_NAME = "scalpv1"
PAPER_MODE = False

# ===📂 Log file ===
LOG_FILE = "trade_log.csv"

# ===📦 Session ===
SESSION = {"CST": "", "X-SECURITY-TOKEN": ""}

# ===✅ Login to IG ===
def login_to_ig():
    url = f"{API_URL}/session"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-IG-API-KEY": API_KEY,
        "Version": "2"
    }
    payload = {
        "identifier": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        SESSION["CST"] = response.headers["CST"]
        SESSION["X-SECURITY-TOKEN"] = response.headers["X-SECURITY-TOKEN"]
        print("[🔐] IG login successful", flush=True)
    else:
        raise Exception(f"IG login failed: {response.text}")

def count_trades_today():
    if not os.path.exists(LOG_FILE):
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    with open(LOG_FILE, newline='') as f:
        return sum(1 for row in csv.reader(f) if row and row[0].startswith(today))

def within_trade_hours():
    now = datetime.now()
    h, m = now.hour, now.minute
    sh, sm, eh, em = TRADE_HOURS
    return (h > sh or (h == sh and m >= sm)) and (h < eh or (h == eh and m <= em))

def has_open_position(epic, headers):
    url = f"{API_URL}/positions"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("[⚠️] Could not verify positions:", response.text, flush=True)
        return False
    for pos in response.json().get("positions", []):
        if pos.get("market", {}).get("epic") == epic:
            print("[🛑] Position already open for", epic, flush=True)
            return True
    return False

def log_trade(trade_data, status, reason=""):
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade_data["direction"],
            trade_data["epic"],
            trade_data["size"],
            trade_data["sl"],
            trade_data["tp"],
            STRATEGY_NAME,
            status,
            reason
        ])

@app.route("/webhook", methods=["POST"])
def webhook():
    print("[👋] Webhook function entered!", flush=True)
    raw = request.data.decode()
    print("[📡] Raw data:", raw, flush=True)
    
    try:
        data = json.loads(raw)
    except Exception as e:
        print("[❌] JSON decode error:", e, flush=True)
        return jsonify({"error": "Invalid JSON"}), 400

    print("[📡] Parsed JSON:", data, flush=True)

    direction = data.get("direction", "").upper()
    epic = data.get("epic")
    size = float(data.get("size", 1))
    stop_distance = float(data.get("sl", 20))
    limit_distance = float(data.get("tp", 30))

    if not within_trade_hours():
        print("[⏰] Out of allowed trading hours", flush=True)
        return jsonify({"status": "skipped", "reason": "Out of trade hours"}), 200

    if count_trades_today() >= MAX_TRADES_PER_DAY:
        print("[🚫] Max trades today reached", flush=True)
        return jsonify({"status": "skipped", "reason": "Max trades reached"}), 200

    try:
        login_to_ig()
    except Exception as e:
        print("[❌] Login failed:", e, flush=True)
        return jsonify({"error": str(e)}), 500

    headers = {
        "X-IG-API-KEY": API_KEY,
        "CST": SESSION["CST"],
        "X-SECURITY-TOKEN": SESSION["X-SECURITY-TOKEN"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2"
    }

    if has_open_position(epic, headers):
        return jsonify({"status": "skipped", "reason": "Open position exists"}), 200

    if PAPER_MODE:
        print("[📝] Paper mode active — trade logged, not sent", flush=True)
        log_trade(data, "paper")
        return jsonify({"status": "paper mode"}), 200

    order_payload = {
        "epic": epic,
        "expiry": "-",
        "direction": direction,
        "size": size,
        "orderType": "MARKET",
        "guaranteedStop": False,
        "stopDistance": stop_distance,
        "limitDistance": limit_distance,
        "forceOpen": True,
        "currencyCode": "GBP",
        "dealReference": STRATEGY_NAME
    }

    response = requests.post(f"{API_URL}/positions/otc", json=order_payload, headers=headers)

    if response.status_code == 200:
        deal_ref = response.json().get("dealReference")
        print("[✅] Trade placed successfully!", flush=True)
        log_trade(data, "executed")
        return jsonify({"status": "executed", "dealReference": deal_ref}), 200
    else:
        print("[❌] Trade failed:", response.text, flush=True)
        log_trade(data, "rejected", response.text)
        return jsonify({"status": "failed", "error": response.text}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
