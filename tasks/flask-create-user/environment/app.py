from flask import Flask, request, jsonify

app = Flask(__name__)
users = []


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    user = {"id": len(users) + 1, "name": data["name"]}
    users.append(user)
    return jsonify(user)


@app.route("/users", methods=["GET"])
def list_users():
    return jsonify(users)
