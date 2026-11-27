#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
from flask import Flask, request, jsonify

app = Flask(__name__)
users = []


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required"}), 400
    user = {"id": len(users) + 1, "name": name.strip()}
    users.append(user)
    return jsonify(user), 201


@app.route("/users", methods=["GET"])
def list_users():
    return jsonify(users)
SOLUTION_EOF
