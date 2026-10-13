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

if __name__ == '__main__':
    threading.Thread(target=checker_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)