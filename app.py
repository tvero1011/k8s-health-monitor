from flask import Flask

import os
import sys

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)