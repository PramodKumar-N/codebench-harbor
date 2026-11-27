from flask import Flask, request, jsonify

app = Flask(__name__)

books = {}
next_id = 1


@app.route("/books", methods=["POST"])
def create_book():
    global next_id
    data = request.get_json()
    book = {"id": next_id, "title": data["title"], "author": data.get("author", "")}
    books[next_id] = book
    next_id += 1
    return jsonify(book), 201


@app.route("/books", methods=["GET"])
def list_books():
    return jsonify(list(books.values()))


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    return jsonify(books[book_id])


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json()
    books[book_id] = {"id": book_id, **data}
    return jsonify(books[book_id])


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    books.pop(book_id, None)
    return "", 204
