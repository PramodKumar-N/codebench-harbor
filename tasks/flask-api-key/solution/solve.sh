#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
import hmac

from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "secret123"


@app.route("/public")
def public():
    return jsonify({"message": "hello"})


@app.route("/secret")
def secret():
    key = request.headers.get("X-API-Key", "")
    if not key:
        return jsonify({"error": "missing api key"}), 401
    if not hmac.compare_digest(key.encode(), API_KEY.encode()):
        return jsonify({"error": "invalid api key"}), 403
    return jsonify({"secret": "the cake is a lie"})
SOLUTION_EOF
