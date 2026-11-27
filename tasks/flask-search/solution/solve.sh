#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["Apple", "apple pie", "Banana", "Cherry Pie", "grape"]


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"results": []})
    results = [item for item in ITEMS if q in item.lower()]
    return jsonify({"results": results})
SOLUTION_EOF
