#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["item-%d" % i for i in range(1, 26)]


def bad_request():
    return jsonify({"error": "invalid pagination"}), 400


@app.route("/items")
def items():
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "10"))
    except ValueError:
        return bad_request()
    if page < 1 or per_page < 1 or per_page > 50:
        return bad_request()
    total = len(ITEMS)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "items": ITEMS[start:start + per_page],
    })
SOLUTION_EOF
