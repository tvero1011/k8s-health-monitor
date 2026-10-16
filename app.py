from flask import Flask, jsonify

import requests
import os
import sys
import threading
import time


def require_env(name):
    value = os.environ.get(name)
    if not value:
        print(f"FATAL: required env var {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value

MONITOR_TARGETS = [u.strip() for u in require_env("MONITOR_TARGETS").split(",")]
CHECK_INTERVAL = int(require_env("CHECK_INTERVAL_SECONDS"))
API_TOKEN = require_env("API_TOKEN")

app = Flask(__name__)
@app.route('/healthz')
def healthz():
    return 'OK', 200

def check_target(url):
    try:
        r = requests.get(url, timeout=5)
        return {"up": r.status_code < 400, "status_code": r.status_code}
    except requests.RequestException as e:
        return {"up": False, "error": type(e).__name__}

@app.route('/status')
def status():
    return jsonify(latest_results)

latest_results = {}
def run_checks():
    for url in MONITOR_TARGETS:
        latest_results[url] = check_target(url)

def checker_loop():
    while True:
        run_checks()
        time.sleep(CHECK_INTERVAL)

@app.route('/ready')
def ready():
    if len(latest_results) == len(MONITOR_TARGETS):
        return 'READY', 200
    return 'NOT READY', 503

@app.route('/metrics')
def metrics():
    up = sum(1 for r in latest_results.values() if r["up"])
    return jsonify(targets_total=len(MONITOR_TARGETS), targets_up=up,
                   targets_down=len(latest_results) - up)

threading.Thread(target=checker_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)