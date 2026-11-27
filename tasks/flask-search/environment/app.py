from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["Apple", "apple pie", "Banana", "Cherry Pie", "grape"]


@app.route("/search")
def search():
    q = request.args.get("q")
    results = [item for item in ITEMS if q in item]
    return jsonify({"results": results})
