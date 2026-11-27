#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
from flask import Flask, request, jsonify

app = Flask(__name__)

books = {}
next_id = 1


def error(message, status):
    return jsonify({"error": message}), status


def read_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


@app.route("/books", methods=["POST"])
def create_book():
    global next_id
    data = read_json()
    title = data.get("title")
    if not is_text(title):
        return error("title is required", 400)
    author = data.get("author", "")
    if not isinstance(author, str):
        return error("author must be a string", 400)
    title, author = title.strip(), author.strip()
    for existing in books.values():
        if existing["title"].lower() == title.lower() and existing["author"].lower() == author.lower():
            return error("book already exists", 409)
    book = {"id": next_id, "title": title, "author": author}
    books[next_id] = book
    next_id += 1
    return jsonify(book), 201


@app.route("/books", methods=["GET"])
def list_books():
    result = sorted(books.values(), key=lambda b: b["id"])
    author = request.args.get("author")
    if author is not None:
        wanted = author.strip().lower()
        result = [b for b in result if b["author"].lower() == wanted]
    return jsonify(result)


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = books.get(book_id)
    if book is None:
        return error("not found", 404)
    return jsonify(book)


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    book = books.get(book_id)
    if book is None:
        return error("not found", 404)
    data = read_json()
    if "title" in data and not is_text(data["title"]):
        return error("title must be a non-empty string", 400)
    if "author" in data and not isinstance(data["author"], str):
        return error("author must be a string", 400)
    if "title" in data:
        book["title"] = data["title"].strip()
    if "author" in data:
        book["author"] = data["author"].strip()
    return jsonify(book)


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    if book_id not in books:
        return error("not found", 404)
    del books[book_id]
    return "", 204
SOLUTION_EOF
