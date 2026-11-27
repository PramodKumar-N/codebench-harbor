from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "secret123"


@app.route("/public")
def public():
    return jsonify({"message": "hello"})


@app.route("/secret")
def secret():
    key = request.headers.get("X-API-Key")
    if key and key != API_KEY:
        return jsonify({"error": "invalid key"}), 401
    return jsonify({"secret": "the cake is a lie"})
