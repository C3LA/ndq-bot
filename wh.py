from flask import Flask, request, jsonify
import requests
import json
import os
import csv
from datetime import datetime

app = Flask(__name__)

# === IG Credentials ===
API_KEY = 'your_api_key'
USERNAME = 'your_ig_username'
PASSWORD = 'your_ig_password'
ACCOUNT_ID = 'your_account_id'
API_URL = 'https://api.ig.com/gateway/deal'

# === Bot Config ===
MAX_TRADES_PER_DAY = 5
TRADE_HOURS = (9, 30, 17, 0)
PAPER_MODE = False
LOG_FILE = "trade_log.csv"

# === IG Session Storage ===
SESSION = {
    "CST": None,
    "X-SECURITY-TOKEN": None
}

# === Auto-login at startup ===
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
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        SESSION["CST"] = res.headers["CST"]
        SESSION["X-SECURITY-TOKEN"] = res.headers["X-SECURITY-TOKEN"]
        print("[🔐] IG login successful", flush=True)
    else:
        raise Exception(f"Login failed: {res.text}")

def get_ig_headers():
    return {
        "X-IG-API-KEY": API_KEY,
        "CST": SESSION["CST"],
        "X-SECURITY-TOKEN": SESSION["X-SECURITY-TOKEN"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2"
    }

def within_trade_hours():
    now = datetime.now()
    h, m = now.hour, now.minute
    sh, sm, eh, em = TRADE_HOURS
    return (h > sh or (h == sh and m >= sm)) and (h < eh or (h == eh and m <= em))

def count_trades_today():
    if not os.path.exists(LOG_FILE):
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    with open(LOG_FILE, newline='') as f:
        return sum(1 for row in csv.reader(f) if row and row[0].startswith(today))

def log_trade(data, status, reason=""):
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("strategy", "unknown"),
            data.get("direction"),
            data.get("epic"),
            data.get("size"),
            data.get("sl"),
            data.get("tp"),
            status,
            reason
        ])

@app.route("/webhook", methods=["POST"])
def webhook():
    print("[👋] Webhook hit!", flush=True)
    try:
        data = json.loads(request.data.decode())
        print("[📡] Webhook payload:", data, flush=True)
    except Exception as e:
        print("[❌] Failed to parse JSON:", e, flush=True)
        return jsonify({"error": "Invalid JSON"}), 400

    # Basic validation
    direction = data.get("direction", "").upper()
    epic = data.get("epic")
    strategy = data.get("strategy", "scalpv1")
    size = float(data.get("size", 1))
    stop_distance = float(data.get("sl", 20))
    limit_distance = float(data.get("tp", 30))

    if not all([direction, epic]):
        return jsonify({"error": "Missing required fields"}), 400

    if not within_trade_hours():
        print("[⏰] Outside allowed trade hours", flush=True)
        log_trade(data, "skipped", "out of hours")
        return jsonify({"status": "skipped - time"}), 200

    if count_trades_today() >= MAX_TRADES_PER_DAY:
        print("[🚫] Max trades reached today", flush=True)
        log_trade(data, "skipped", "max trades reached")
        return jsonify({"status": "skipped - limit"}), 200

    if not SESSION["CST"] or not SESSION["X-SECURITY-TOKEN"]:
        try:
            login_to_ig()
        except Exception as e:
            print("[❌] Login failed:", e, flush=True)
            return jsonify({"error": str(e)}), 500

    if PAPER_MODE:
        print("[📝] Paper mode active — skipping real trade", flush=True)
        log_trade(data, "paper")
        return jsonify({"status": "paper"}), 200

    headers = get_ig_headers()

    # Prepare trade
    payload = {
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
        "dealReference": strategy
    }

    # Submit order
    res = requests.post(f"{API_URL}/positions/otc", json=payload, headers=headers)
    if res.status_code == 200:
        print("[✅] Trade placed!", flush=True)
        log_trade(data, "executed")
        return jsonify({"status": "executed"}), 200
    else:
        print("[❌] Trade failed:", res.text, flush=True)
        log_trade(data, "failed", res.text)
        return jsonify({"error": res.text}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    try:
        login_to_ig()
    except Exception as e:
        print("[❌] Login error at startup:", e, flush=True)
    app.run(host="0.0.0.0", port=port)
