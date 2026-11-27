from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["item-%d" % i for i in range(1, 26)]


@app.route("/items")
def items():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    start = page * per_page
    end = start + per_page
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": len(ITEMS),
        "items": ITEMS[start:end],
    })
