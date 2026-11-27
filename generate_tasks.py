#!/usr/bin/env python3
"""
CodeBench - generates 15 Harbor tasks (and can check that every task is fair).

Usage (run from the project root, with the virtual environment active):

    python generate_tasks.py --check     # local test, no Docker needed
    python generate_tasks.py             # writes the 15 task folders into ./tasks

--check needs:  pip install pytest flask
For each task it checks two things:
    1. the broken starter code FAILS the tests   (task is not already solved)
    2. the reference solution PASSES the tests   (task is fair and solvable)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ORG = "my-org"

# ----------------------------------------------------------------------------
# Shared pieces
# ----------------------------------------------------------------------------

HEADER = '''import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
'''

FLASK_CLIENT = '''import importlib


def make_client():
    """Fresh copy of the app (empty data) for every test."""
    import app as module
    importlib.reload(module)
    return module.app.test_client()
'''

TEST_SH = '''#!/bin/bash
mkdir -p /logs/verifier
cd /app
python -m pytest /tests/test_outputs.py -q
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
'''

# ----------------------------------------------------------------------------
# SQL data (used by the 4 SQL tasks)
# ----------------------------------------------------------------------------

CUSTOMERS = [
    (1, "Asha Rao", "Bengaluru"),
    (2, "Bala Kumar", "Chennai"),
    (3, "Chitra Iyer", "Bengaluru"),
    (4, "Dev Patel", "Mumbai"),
    (5, "Esha Gupta", "Mumbai"),
    (6, "Farhan Ali", "Chennai"),
    (7, "Gita Nair", "Kochi"),
    (8, "Hari Singh", "Bengaluru"),
]

ORDERS = [  # (id, customer_id, amount, order_date)
    (1, 1, 3000, "2025-01-10"),
    (2, 1, 2500, "2025-02-15"),
    (3, 2, 1200, "2025-01-20"),
    (4, 3, 5200, "2025-03-05"),
    (5, 4, 800, "2025-01-25"),
    (6, 4, 4500, "2025-02-28"),
    (7, 2, 300, "2025-03-15"),
    (8, 1, 700, "2025-04-02"),
    (9, 5, 6000, "2025-04-10"),
    (10, 3, 150, "2025-04-20"),
    (11, 6, 2200, "2025-02-05"),
    (12, 6, 2900, "2025-03-25"),
    (13, 4, 1000, "2025-05-01"),
    (14, 5, 100, "2025-05-05"),
    (15, 2, 4000, "2025-05-20"),
    (16, 1, 50, "2025-06-01"),
]

SETUP_DB = '''import os
import sqlite3

path = os.path.join(os.environ.get("APP_DIR", "/app"), "shop.db")
if os.path.exists(path):
    os.remove(path)
con = sqlite3.connect(path)
con.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER, order_date TEXT);
""")
con.executemany("INSERT INTO customers VALUES (?, ?, ?)", __CUSTOMERS__)
con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", __ORDERS__)
con.commit()
con.close()
'''.replace("__CUSTOMERS__", repr(CUSTOMERS)).replace("__ORDERS__", repr(ORDERS))

SCHEMA_TEXT = """The SQLite database is at /app/shop.db. It has two tables:

- customers(id, name, city)
- orders(id, customer_id, amount, order_date)

`amount` is a whole number (rupees). `order_date` is text like 2025-03-05.
`orders.customer_id` points to `customers.id`.

Write your answer as ONE SELECT query in the file /app/query.sql.
Use exactly the column names (aliases) and the ordering given below.
Do not change the database."""

SQL_STARTER = "-- Write your single SELECT query here.\n"

SQL_TEST = HEADER + '''import sqlite3


def run_query():
    with open(os.path.join(APP, "query.sql"), encoding="utf-8") as f:
        sql = f.read()
    con = sqlite3.connect(os.path.join(APP, "shop.db"))
    con.execute("PRAGMA query_only = ON")
    # the database must be untouched
    assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == __N_ORDERS__
    assert con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == __N_CUSTOMERS__
    cur = con.execute(sql)
    assert cur.description is not None, "query.sql must contain one SELECT query"
    columns = [d[0] for d in cur.description]
    rows = [tuple(r) for r in cur.fetchall()]
    return columns, rows


def test_columns():
    columns, _ = run_query()
    assert columns == __COLUMNS__


def test_rows_and_order():
    _, rows = run_query()
    assert rows == __EXPECTED__
'''.replace("__N_ORDERS__", str(len(ORDERS))).replace("__N_CUSTOMERS__", str(len(CUSTOMERS)))


def sql_expected_big_spenders(threshold=5500):
    totals = {}
    for _, cid, amount, _ in ORDERS:
        totals[cid] = totals.get(cid, 0) + amount
    rows = [(name, totals[cid]) for cid, name, _ in CUSTOMERS if totals.get(cid, 0) > threshold]
    return sorted(rows, key=lambda r: -r[1])


def sql_expected_orders_per_city():
    count = {city: 0 for _, _, city in CUSTOMERS}
    city_of = {cid: city for cid, _, city in CUSTOMERS}
    for _, cid, _, _ in ORDERS:
        count[city_of[cid]] += 1
    return sorted(count.items(), key=lambda r: (-r[1], r[0]))


def sql_expected_no_orders():
    ordered = {cid for _, cid, _, _ in ORDERS}
    rows = [(name, city) for cid, name, city in CUSTOMERS if cid not in ordered]
    return sorted(rows)


def sql_expected_top_per_city():
    totals = {}
    for _, cid, amount, _ in ORDERS:
        totals[cid] = totals.get(cid, 0) + amount
    best = {}
    for cid, name, city in CUSTOMERS:
        if cid not in totals:
            continue
        if city not in best or totals[cid] > best[city][1]:
            best[city] = (name, totals[cid])
    return sorted((city, name, total) for city, (name, total) in best.items())


def sql_task(task_id, difficulty, question, columns, expected, solution_sql):
    instruction = SCHEMA_TEXT + "\n\n" + question + "\n\nRequired columns, in this order: " + ", ".join(columns) + "."
    return {
        "id": task_id,
        "type": "SQL",
        "difficulty": difficulty,
        "instruction": instruction,
        "starter": {"query.sql": SQL_STARTER, "setup_db.py": SETUP_DB},
        "solution": {"query.sql": solution_sql},
        "tests": SQL_TEST.replace("__COLUMNS__", repr(columns)).replace("__EXPECTED__", repr(expected)),
        "packages": [],
        "sql": True,
    }


# ----------------------------------------------------------------------------
# Task list
# ----------------------------------------------------------------------------

def build_tasks():
    tasks = []

    # ============================ LOGIC (3) ================================
    tasks.append({
        "id": "fix-find-max", "type": "Logic", "difficulty": "easy",
        "instruction": """The file /app/app.py has a function find_max(nums) that should return
the largest number in a list. It has bugs. Fix it so that:

- it works for lists that contain only negative numbers
- it returns None when the list is empty

Keep the function name and signature the same.""",
        "starter": {"app.py": '''def find_max(nums):
    biggest = 0
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
'''},
        "solution": {"app.py": '''def find_max(nums):
    if not nums:
        return None
    biggest = nums[0]
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
'''},
        "tests": HEADER + '''from app import find_max


def test_normal_list():
    assert find_max([3, 9, 2]) == 9


def test_all_negative():
    assert find_max([-5, -1, -8]) == -1


def test_empty_list():
    assert find_max([]) is None


def test_single_item():
    assert find_max([-7]) == -7


def test_floats_and_duplicates():
    assert find_max([2.5, 2.5, 1.0]) == 2.5


def test_zero_is_a_valid_maximum():
    assert find_max([-3, 0, -1]) == 0
''',
        "packages": [],
    })

    tasks.append({
        "id": "fix-remove-duplicates", "type": "Logic", "difficulty": "medium",
        "instruction": """The file /app/app.py has a function remove_duplicates(items) that should
return a NEW list with duplicate values removed.

Rules:
- keep the FIRST occurrence of each value
- keep the original order
- the items can be anything, including unhashable values such as lists
- do not change the list that was passed in

The current version loses the order and crashes on lists. Fix it.""",
        "starter": {"app.py": '''def remove_duplicates(items):
    return list(set(items))
'''},
        "solution": {"app.py": '''def remove_duplicates(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
'''},
        "tests": HEADER + '''from app import remove_duplicates


def test_keeps_first_occurrence_and_order():
    assert remove_duplicates([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_strings():
    assert remove_duplicates(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_empty():
    assert remove_duplicates([]) == []


def test_unhashable_items():
    assert remove_duplicates([[1], [2], [1], [3]]) == [[1], [2], [3]]


def test_does_not_change_input():
    data = [2, 2, 1]
    remove_duplicates(data)
    assert data == [2, 2, 1]


def test_returns_new_list():
    data = [1, 2]
    assert remove_duplicates(data) is not data
''',
        "packages": [],
    })

    tasks.append({
        "id": "fix-merge-intervals", "type": "Logic", "difficulty": "hard",
        "instruction": """The file /app/app.py has a function merge_intervals(intervals) that takes a
list of [start, end] pairs and merges all overlapping intervals.

Rules:
- intervals that overlap OR touch (for example [1, 2] and [2, 3]) are merged
- the input can be in any order
- an interval can be completely inside another one
- return a new list of [start, end] lists, sorted by start
- do not change the input
- an empty input returns an empty list

The current version has several bugs. Fix it.""",
        "starter": {"app.py": '''def merge_intervals(intervals):
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
'''},
        "solution": {"app.py": '''def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals, key=lambda pair: pair[0]):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
'''},
        "tests": HEADER + '''import copy

from app import merge_intervals


def test_basic_overlap():
    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]


def test_unsorted_input():
    assert merge_intervals([[8, 10], [1, 3], [2, 6]]) == [[1, 6], [8, 10]]


def test_interval_inside_another():
    assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]


def test_touching_intervals_are_merged():
    assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]


def test_empty():
    assert merge_intervals([]) == []


def test_single_interval():
    assert merge_intervals([[5, 7]]) == [[5, 7]]


def test_tuples_in_lists_out():
    assert merge_intervals([(1, 3), (2, 4)]) == [[1, 4]]


def test_input_not_changed():
    data = [[5, 8], [1, 6], [20, 25]]
    before = copy.deepcopy(data)
    merge_intervals(data)
    assert data == before
''',
        "packages": [],
    })

    # ============================ FLASK (5) ================================
    tasks.append({
        "id": "flask-create-user", "type": "Flask", "difficulty": "easy",
        "instruction": """The file /app/app.py is a small Flask API with two routes:
POST /users and GET /users. The POST route is buggy. Fix it so that:

- a valid request {"name": "Asha"} returns status 201 and the JSON {"id": 1, "name": "Asha"}
  (ids go 1, 2, 3 ...)
- the name is trimmed: "  Asha " is saved as "Asha"
- a missing name, an empty name, a name with only spaces, a name that is not a string,
  or a request with no JSON body returns status 400 and the JSON {"error": "name is required"}
- GET /users keeps returning the list of saved users""",
        "starter": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "solution": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "tests": HEADER + FLASK_CLIENT + '''

def test_create_user():
    client = make_client()
    r = client.post("/users", json={"name": "Asha"})
    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "name": "Asha"}


def test_ids_increase_and_list_works():
    client = make_client()
    client.post("/users", json={"name": "Asha"})
    r = client.post("/users", json={"name": "Bala"})
    assert r.get_json() == {"id": 2, "name": "Bala"}
    listing = client.get("/users").get_json()
    assert listing == [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Bala"}]


def test_name_is_trimmed():
    client = make_client()
    r = client.post("/users", json={"name": "  Asha "})
    assert r.status_code == 201
    assert r.get_json()["name"] == "Asha"


def test_missing_or_bad_name_is_400():
    client = make_client()
    for body in [{}, {"name": ""}, {"name": "   "}, {"name": 123}, {"other": "x"}]:
        r = client.post("/users", json=body)
        assert r.status_code == 400, body
        assert r.get_json() == {"error": "name is required"}


def test_no_json_body_is_400():
    client = make_client()
    r = client.post("/users")
    assert r.status_code == 400
    assert r.get_json() == {"error": "name is required"}


def test_bad_requests_do_not_create_users():
    client = make_client()
    client.post("/users", json={})
    assert client.get("/users").get_json() == []
''',
        "packages": ["flask"],
    })

    tasks.append({
        "id": "flask-search", "type": "Flask", "difficulty": "medium",
        "instruction": """The file /app/app.py is a Flask API with a route GET /search?q=... that
searches a fixed list of items. It is buggy. Fix it so that:

- the search is case-insensitive and matches any part of the item text
  (q=pie finds "apple pie" and "Cherry Pie")
- results keep the original order and the original spelling of the items
- spaces around q are ignored (q=" banana " works like q=banana)
- if q is missing or empty, return status 200 and {"results": []}
- the response is always JSON in the form {"results": [...]}""",
        "starter": {"app.py": '''from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["Apple", "apple pie", "Banana", "Cherry Pie", "grape"]


@app.route("/search")
def search():
    q = request.args.get("q")
    results = [item for item in ITEMS if q in item]
    return jsonify({"results": results})
'''},
        "solution": {"app.py": '''from flask import Flask, request, jsonify

app = Flask(__name__)

ITEMS = ["Apple", "apple pie", "Banana", "Cherry Pie", "grape"]


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"results": []})
    results = [item for item in ITEMS if q in item.lower()]
    return jsonify({"results": results})
'''},
        "tests": HEADER + FLASK_CLIENT + '''

def search(client, q):
    r = client.get("/search", query_string=q)
    assert r.status_code == 200
    return r.get_json()


def test_case_insensitive_substring():
    client = make_client()
    assert search(client, {"q": "apple"}) == {"results": ["Apple", "apple pie"]}


def test_uppercase_query():
    client = make_client()
    assert search(client, {"q": "PIE"}) == {"results": ["apple pie", "Cherry Pie"]}


def test_spaces_around_query_are_ignored():
    client = make_client()
    assert search(client, {"q": " banana "}) == {"results": ["Banana"]}


def test_no_match():
    client = make_client()
    assert search(client, {"q": "zzz"}) == {"results": []}


def test_missing_q():
    client = make_client()
    assert search(client, {}) == {"results": []}


def test_empty_q():
    client = make_client()
    assert search(client, {"q": ""}) == {"results": []}
    assert search(client, {"q": "   "}) == {"results": []}
''',
        "packages": ["flask"],
    })

    tasks.append({
        "id": "flask-pagination", "type": "Flask", "difficulty": "medium",
        "instruction": """The file /app/app.py is a Flask API with GET /items that returns a list of
25 items with pagination. It is buggy. Fix it so that:

- pages start at 1 (page=1 is the first page); the defaults are page=1 and per_page=10
- the JSON response has exactly these keys:
  page, per_page, total, total_pages, items
- total is the number of all items (25); total_pages is the number of pages needed
  (for example 3 when per_page=10)
- a page after the last one returns status 200 with "items": []
- page must be an integer >= 1, and per_page must be an integer from 1 to 50;
  anything else (0, -1, abc, 1.5, 51 ...) returns status 400 and {"error": "invalid pagination"}""",
        "starter": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "solution": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "tests": HEADER + FLASK_CLIENT + '''

def names(a, b):
    return ["item-%d" % i for i in range(a, b + 1)]


def test_default_is_first_page_of_ten():
    client = make_client()
    r = client.get("/items")
    assert r.status_code == 200
    assert r.get_json() == {
        "page": 1, "per_page": 10, "total": 25, "total_pages": 3, "items": names(1, 10),
    }


def test_last_page_is_shorter():
    client = make_client()
    data = client.get("/items?page=3").get_json()
    assert data["items"] == names(21, 25)
    assert data["page"] == 3


def test_page_after_last_is_empty():
    client = make_client()
    r = client.get("/items?page=4")
    assert r.status_code == 200
    assert r.get_json()["items"] == []


def test_custom_page_size():
    client = make_client()
    data = client.get("/items?per_page=5&page=2").get_json()
    assert data["items"] == names(6, 10)
    assert data["total_pages"] == 5
    assert data["per_page"] == 5


def test_exact_division():
    client = make_client()
    data = client.get("/items?per_page=25").get_json()
    assert data["total_pages"] == 1
    assert len(data["items"]) == 25


def test_invalid_values_are_400():
    client = make_client()
    for query in ["page=0", "page=-1", "page=abc", "page=1.5",
                  "per_page=0", "per_page=51", "per_page=x", "per_page=-5"]:
        r = client.get("/items?" + query)
        assert r.status_code == 400, query
        assert r.get_json() == {"error": "invalid pagination"}
''',
        "packages": ["flask"],
    })

    tasks.append({
        "id": "flask-api-key", "type": "Flask", "difficulty": "medium",
        "instruction": """The file /app/app.py is a Flask API with a public route (GET /public) and a
protected route (GET /secret). The protection is broken. Fix GET /secret so that:

- the header X-API-Key must equal "secret123"
- header missing or empty: status 401 and {"error": "missing api key"}
- header present but wrong: status 403 and {"error": "invalid api key"}
- header correct: status 200 and {"secret": "the cake is a lie"}
- the key comparison must be case-sensitive ("SECRET123" is wrong)

GET /public must stay open to everyone and keep working.""",
        "starter": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "solution": {"app.py": '''import hmac

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
'''},
        "tests": HEADER + FLASK_CLIENT + '''

def test_public_is_open():
    client = make_client()
    r = client.get("/public")
    assert r.status_code == 200
    assert r.get_json() == {"message": "hello"}


def test_correct_key():
    client = make_client()
    r = client.get("/secret", headers={"X-API-Key": "secret123"})
    assert r.status_code == 200
    assert r.get_json() == {"secret": "the cake is a lie"}


def test_missing_key_is_401():
    client = make_client()
    r = client.get("/secret")
    assert r.status_code == 401
    assert r.get_json() == {"error": "missing api key"}


def test_empty_key_is_401():
    client = make_client()
    r = client.get("/secret", headers={"X-API-Key": ""})
    assert r.status_code == 401
    assert r.get_json() == {"error": "missing api key"}


def test_wrong_key_is_403():
    client = make_client()
    r = client.get("/secret", headers={"X-API-Key": "nope"})
    assert r.status_code == 403
    assert r.get_json() == {"error": "invalid api key"}


def test_key_is_case_sensitive():
    client = make_client()
    r = client.get("/secret", headers={"X-API-Key": "SECRET123"})
    assert r.status_code == 403
''',
        "packages": ["flask"],
    })

    tasks.append({
        "id": "flask-books-crud", "type": "Flask", "difficulty": "hard",
        "instruction": """The file /app/app.py is a small in-memory "books" API. Several routes are
buggy or incomplete. Make it follow these rules. Errors are always JSON:
{"error": "<message>"} (any message text is fine).

POST /books  body {"title": ..., "author": ...}
- title is required and must be a non-empty string (spaces only does not count) -> else 400
- author is optional (default ""), but if given it must be a string -> else 400
- title and author are trimmed
- a book with the same title AND same author (ignoring upper/lower case) already exists -> 409
  (same title with a different author is allowed)
- success: 201 and {"id", "title", "author"}; ids start at 1 and are never reused

GET /books
- returns all books as a list sorted by id
- optional ?author=NAME returns only books by that author (ignoring case)

GET /books/<id>   -> the book, or 404 if it does not exist

PUT /books/<id>
- only "title" and "author" can be changed, and only the fields that are sent
  (a partial update keeps the other fields); "id" can never change
- title, if sent, must be a non-empty string -> else 400
- 404 if the book does not exist; success returns 200 and the updated book

DELETE /books/<id>  -> 204 with no body, or 404 if it does not exist""",
        "starter": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "solution": {"app.py": '''from flask import Flask, request, jsonify

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
'''},
        "tests": HEADER + FLASK_CLIENT + '''

def add(client, title, author=None):
    body = {"title": title}
    if author is not None:
        body["author"] = author
    return client.post("/books", json=body)


def test_create_book():
    client = make_client()
    r = add(client, "Dune", "Frank Herbert")
    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "title": "Dune", "author": "Frank Herbert"}


def test_author_is_optional_and_values_are_trimmed():
    client = make_client()
    r = add(client, "  Emma  ")
    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "title": "Emma", "author": ""}


def test_create_validation():
    client = make_client()
    assert client.post("/books", json={}).status_code == 400
    assert client.post("/books", json={"title": "   "}).status_code == 400
    assert client.post("/books", json={"title": 5}).status_code == 400
    assert client.post("/books", json={"title": "X", "author": 7}).status_code == 400
    assert client.post("/books").status_code == 400
    assert client.get("/books").get_json() == []


def test_duplicate_is_conflict():
    client = make_client()
    add(client, "Dune", "Frank Herbert")
    assert add(client, "  dune ", "FRANK HERBERT").status_code == 409
    assert add(client, "Dune", "Someone Else").status_code == 201


def test_list_is_sorted_and_can_filter_by_author():
    client = make_client()
    add(client, "B", "Zed")
    add(client, "A", "Amy")
    add(client, "C", "zed")
    assert [b["id"] for b in client.get("/books").get_json()] == [1, 2, 3]
    zed = client.get("/books?author=ZED").get_json()
    assert [b["title"] for b in zed] == ["B", "C"]
    assert client.get("/books?author=nobody").get_json() == []


def test_get_one_and_404():
    client = make_client()
    add(client, "Dune", "Frank Herbert")
    assert client.get("/books/1").get_json()["title"] == "Dune"
    r = client.get("/books/99")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_put_is_a_partial_update():
    client = make_client()
    add(client, "Dune", "Frank Herbert")
    r = client.put("/books/1", json={"author": "F. Herbert"})
    assert r.status_code == 200
    assert r.get_json() == {"id": 1, "title": "Dune", "author": "F. Herbert"}


def test_put_cannot_change_id_and_validates_title():
    client = make_client()
    add(client, "Dune", "Frank Herbert")
    r = client.put("/books/1", json={"id": 99, "title": "Dune Messiah"})
    assert r.status_code == 200
    assert r.get_json() == {"id": 1, "title": "Dune Messiah", "author": "Frank Herbert"}
    assert client.get("/books/99").status_code == 404
    assert client.put("/books/1", json={"title": "  "}).status_code == 400
    assert client.get("/books/1").get_json()["title"] == "Dune Messiah"


def test_put_missing_book_is_404():
    client = make_client()
    r = client.put("/books/5", json={"title": "Ghost"})
    assert r.status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_and_ids_are_not_reused():
    client = make_client()
    add(client, "One", "A")
    add(client, "Two", "B")
    r = client.delete("/books/1")
    assert r.status_code == 204
    assert r.data == b""
    assert client.get("/books/1").status_code == 404
    assert client.delete("/books/1").status_code == 404
    assert add(client, "Three", "C").get_json()["id"] == 3
''',
        "packages": ["flask"],
    })

    # ============================== SQL (4) ================================
    tasks.append(sql_task(
        "sql-big-spenders", "easy",
        "Task: list the customers whose TOTAL order amount is MORE than 5500 (strictly more).\n"
        "Show the customer name and the total. Sort by total_spent, highest first.",
        ["name", "total_spent"], sql_expected_big_spenders(),
        """SELECT c.name AS name, SUM(o.amount) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name
HAVING SUM(o.amount) > 5500
ORDER BY total_spent DESC;
"""))

    tasks.append(sql_task(
        "sql-orders-per-city", "medium",
        "Task: count how many orders were placed by customers of each city.\n"
        "EVERY city that has at least one customer must appear, even if its count is 0.\n"
        "Sort by order_count (highest first), then by city (A to Z).",
        ["city", "order_count"], sql_expected_orders_per_city(),
        """SELECT c.city AS city, COUNT(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.city
ORDER BY order_count DESC, city ASC;
"""))

    tasks.append(sql_task(
        "sql-no-orders", "medium",
        "Task: find the customers who have never placed any order.\n"
        "Sort by name (A to Z).",
        ["name", "city"], sql_expected_no_orders(),
        """SELECT c.name AS name, c.city AS city
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL
ORDER BY c.name;
"""))

    tasks.append(sql_task(
        "sql-top-spender-per-city", "hard",
        "Task: for each city, find the customer with the highest TOTAL order amount.\n"
        "Only customers with at least one order count, and a city with no orders at all\n"
        "does not appear. Show the city, the customer name and the total.\n"
        "Sort by city (A to Z). (There are no ties in this data.)",
        ["city", "name", "total_spent"], sql_expected_top_per_city(),
        """WITH totals AS (
    SELECT c.city AS city, c.name AS name, SUM(o.amount) AS total_spent
    FROM customers c
    JOIN orders o ON o.customer_id = c.id
    GROUP BY c.id, c.city, c.name
)
SELECT city, name, total_spent
FROM totals t
WHERE total_spent = (SELECT MAX(total_spent) FROM totals WHERE city = t.city)
ORDER BY city;
"""))

    # =========================== DATA CLEANING (3) =========================
    csv_helpers = '''import csv

from clean import clean_csv


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def run(tmp_path, rows):
    src = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    write_csv(src, rows)
    clean_csv(str(src), str(out))
    return read_csv(out)
'''

    stub = '''def clean_csv(input_path, output_path):
    """Read the CSV at input_path and write the cleaned CSV to output_path."""
    raise NotImplementedError
'''

    tasks.append({
        "id": "data-trim-and-dedupe", "type": "Data cleaning", "difficulty": "easy",
        "instruction": """Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV file with the header name,email,city and writes a cleaned CSV
(also with a header) to output_path. A small example of the input format is in
/app/sample_messy.csv.

Cleaning rules:
1. remove spaces at the start and end of EVERY value
2. remove rows whose email is empty (after trimming)
3. remove duplicate rows: rows that are exactly the same after trimming
   (keep the first one; rows that differ in any column are NOT duplicates)
4. keep the original row order and the same header""",
        "starter": {
            "clean.py": stub,
            "sample_messy.csv": "name,email,city\n  Asha ,asha@x.com, Bengaluru\nBala,,Chennai\nAsha,asha@x.com,Bengaluru\n",
        },
        "solution": {"clean.py": '''import csv


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    email_index = header.index("email") if "email" in header else 0
    seen = set()
    cleaned = []
    for row in rows:
        row = [value.strip() for value in row]
        if len(row) <= email_index or not row[email_index]:
            continue
        key = tuple(row)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
'''},
        "tests": HEADER + csv_helpers + '''

HEADER_ROW = ["name", "email", "city"]


def test_trim_drop_empty_email_and_exact_duplicates(tmp_path):
    rows = [
        HEADER_ROW,
        ["  Asha ", "asha@x.com", " Bengaluru"],
        ["Bala", "", "Chennai"],
        ["Asha", "asha@x.com", "Bengaluru"],
        ["Chitra", "  chitra@x.com  ", "Mumbai"],
        ["Chitra", "chitra@x.com", "Pune"],
        ["Dev", "   ", "Goa"],
    ]
    assert run(tmp_path, rows) == [
        HEADER_ROW,
        ["Asha", "asha@x.com", "Bengaluru"],
        ["Chitra", "chitra@x.com", "Mumbai"],
        ["Chitra", "chitra@x.com", "Pune"],
    ]


def test_order_is_kept(tmp_path):
    rows = [HEADER_ROW, ["Z", "z@x.com", "A"], ["A", "a@x.com", "B"], ["M", "m@x.com", "C"]]
    assert run(tmp_path, rows) == rows


def test_header_only(tmp_path):
    assert run(tmp_path, [HEADER_ROW]) == [HEADER_ROW]


def test_nothing_to_remove(tmp_path):
    rows = [HEADER_ROW, ["Asha", "asha@x.com", "Bengaluru"]]
    assert run(tmp_path, rows) == rows
''',
        "packages": [],
    })

    tasks.append({
        "id": "data-normalize-fields", "type": "Data cleaning", "difficulty": "medium",
        "instruction": """Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV with the header name,email,phone,joined and writes a cleaned CSV
(with the same header) to output_path. Every row is kept, in the same order.
A small example of the input is in /app/sample_messy.csv.

Rules for each value (first remove spaces at both ends):
- name: make each word start with a capital letter and the rest lowercase, and
  replace repeated inner spaces with one space ("  asha   RAO " -> "Asha Rao")
- email: lowercase
- phone: keep only the digits. If there are more than 10 digits keep the LAST 10.
  If there are fewer than 10 digits, the result is an empty value.
- joined: convert to the ISO format YYYY-MM-DD. The input can be written as
  YYYY-MM-DD, DD/MM/YYYY or DD-Mon-YYYY (for example 05-Nov-2025).
  Anything else, or a date that does not exist (for example 31/02/2025), becomes an empty value.""",
        "starter": {
            "clean.py": stub,
            "sample_messy.csv": "name,email,phone,joined\n  asha   RAO ,ASHA@Example.COM,+91 98441-42846,05-Nov-2025\nBala kumar,bala@x.com,12345,31/12/2025\n",
        },
        "solution": {"clean.py": '''import csv
from datetime import datetime

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]


def normalize_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def normalize_phone(text):
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else ""


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    index = {name: i for i, name in enumerate(header)}
    cleaned = []
    for row in rows:
        row = [value.strip() for value in row]
        row += [""] * (len(header) - len(row))
        row[index["name"]] = " ".join(row[index["name"]].split()).title()
        row[index["email"]] = row[index["email"]].lower()
        row[index["phone"]] = normalize_phone(row[index["phone"]])
        row[index["joined"]] = normalize_date(row[index["joined"]])
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
'''},
        "tests": HEADER + csv_helpers + '''

HEADER_ROW = ["name", "email", "phone", "joined"]


def test_all_rules(tmp_path):
    rows = [
        HEADER_ROW,
        ["  asha   rao ", "ASHA@Example.COM", "+91 98441-42846", "05-Nov-2025"],
        ["BALA kumar", "bala@x.com", "12345", "31/12/2025"],
        ["chitra iyer", "c@x.com", "080 2345 6789", "2025-02-30"],
        ["Dev Patel", " d@x.com ", "(022) 4000-1234", "15/13/2025"],
        ["esha gupta", "e@x.com", "9876543210", "2024-07-04"],
    ]
    assert run(tmp_path, rows) == [
        HEADER_ROW,
        ["Asha Rao", "asha@example.com", "9844142846", "2025-11-05"],
        ["Bala Kumar", "bala@x.com", "", "2025-12-31"],
        ["Chitra Iyer", "c@x.com", "8023456789", ""],
        ["Dev Patel", "d@x.com", "2240001234", ""],
        ["Esha Gupta", "e@x.com", "9876543210", "2024-07-04"],
    ]


def test_dates_in_all_three_formats(tmp_path):
    rows = [
        HEADER_ROW,
        ["a", "a@x.com", "1111111111", "2025-01-09"],
        ["b", "b@x.com", "1111111111", "09/01/2025"],
        ["c", "c@x.com", "1111111111", "09-Jan-2025"],
        ["d", "d@x.com", "1111111111", "January 9, 2025"],
        ["e", "e@x.com", "1111111111", ""],
    ]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["2025-01-09", "2025-01-09", "2025-01-09", "", ""]


def test_leap_day(tmp_path):
    rows = [HEADER_ROW, ["a", "a@x.com", "1111111111", "29/02/2024"],
            ["b", "b@x.com", "1111111111", "29/02/2025"]]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["2024-02-29", ""]


def test_every_row_is_kept_in_order(tmp_path):
    rows = [HEADER_ROW] + [["n%d" % i, "e%d@x.com" % i, "", ""] for i in range(5)]
    result = run(tmp_path, rows)
    assert [r[1] for r in result[1:]] == ["e%d@x.com" % i for i in range(5)]
''',
        "packages": [],
    })

    tasks.append({
        "id": "data-merge-customers", "type": "Data cleaning", "difficulty": "hard",
        "instruction": """Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV with the header name,email,city,amount,updated and writes a cleaned
CSV (with the same header) to output_path. A small example is in /app/sample_messy.csv.

Rules, in this order:
1. remove spaces at both ends of every value
2. email: make it lowercase; remove rows whose email is empty or has no "@"
3. the same email can appear several times (compare after lowercasing). Keep only ONE row
   per email: the one with the latest `updated` date (dates are YYYY-MM-DD text).
   If two rows have the same date, keep the one that appears LATER in the file.
   The kept row's own values are used (do not mix values from different rows).
4. city: if empty, write "Unknown"
5. amount: remove "$" and "," characters, then write it with exactly 2 decimals
   ("$1,200.5" -> "1200.50", "-12.5" -> "-12.50"). If it is empty or not a number
   (for example "abc" or "nan"), write "0.00".
6. sort the final rows by email, A to Z""",
        "starter": {
            "clean.py": stub,
            "sample_messy.csv": "name,email,city,amount,updated\nAsha,ASHA@x.com,Bengaluru,\"$1,200.50\",2025-01-10\nAsha R,asha@x.com ,,$1500,2025-03-01\nNoEmail,,Pune,10,2025-01-01\n",
        },
        "solution": {"clean.py": '''import csv
import math


def clean_amount(text):
    text = text.replace("$", "").replace(",", "").strip()
    try:
        value = float(text)
    except ValueError:
        return "0.00"
    if not math.isfinite(value):
        return "0.00"
    return "%.2f" % value


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    index = {name: i for i, name in enumerate(header)}
    best = {}
    for row in rows:
        row = [value.strip() for value in row]
        row += [""] * (len(header) - len(row))
        email = row[index["email"]].lower()
        if not email or "@" not in email:
            continue
        row[index["email"]] = email
        if email not in best or row[index["updated"]] >= best[email][index["updated"]]:
            best[email] = row
    cleaned = []
    for email in sorted(best):
        row = best[email]
        if not row[index["city"]]:
            row[index["city"]] = "Unknown"
        row[index["amount"]] = clean_amount(row[index["amount"]])
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
'''},
        "tests": HEADER + csv_helpers + '''

HEADER_ROW = ["name", "email", "city", "amount", "updated"]


def test_full_example(tmp_path):
    rows = [
        HEADER_ROW,
        ["Asha", "ASHA@x.com", "Bengaluru", "$1,200.50", "2025-01-10"],
        ["Asha R", "asha@x.com ", "", "$1,500", "2025-03-01"],
        ["Bala", "bala@x.com", "Chennai", "abc", "2025-02-01"],
        ["NoEmail", "", "Pune", "10", "2025-01-01"],
        ["BadEmail", "not-an-email", "Pune", "10", "2025-01-01"],
        ["Chitra", "chitra@x.com", "Mumbai", "-12.5", "2025-05-05"],
        ["Chitra Old", "chitra@x.com", "Delhi", "99", "2025-05-05"],
        ["Dev", "dev@x.com", "Goa", "", "2025-04-04"],
    ]
    assert run(tmp_path, rows) == [
        HEADER_ROW,
        ["Asha R", "asha@x.com", "Unknown", "1500.00", "2025-03-01"],
        ["Bala", "bala@x.com", "Chennai", "0.00", "2025-02-01"],
        ["Chitra Old", "chitra@x.com", "Delhi", "99.00", "2025-05-05"],
        ["Dev", "dev@x.com", "Goa", "0.00", "2025-04-04"],
    ]


def test_latest_date_wins_even_if_it_comes_first(tmp_path):
    rows = [
        HEADER_ROW,
        ["New", "a@x.com", "Pune", "5", "2025-06-01"],
        ["Old", "A@x.com", "Goa", "9", "2025-01-01"],
    ]
    assert run(tmp_path, rows) == [HEADER_ROW, ["New", "a@x.com", "Pune", "5.00", "2025-06-01"]]


def test_rows_are_sorted_by_email(tmp_path):
    rows = [
        HEADER_ROW,
        ["Z", "z@x.com", "c", "1", "2025-01-01"],
        ["A", "a@x.com", "c", "1", "2025-01-01"],
        ["M", "m@x.com", "c", "1", "2025-01-01"],
    ]
    result = run(tmp_path, rows)
    assert [r[1] for r in result[1:]] == ["a@x.com", "m@x.com", "z@x.com"]


def test_amount_formats(tmp_path):
    amounts = ["$1,234,567.891", "7", "nan", "  $ 3.5 ", "-0.456", "1e2"]
    rows = [HEADER_ROW] + [["n", "u%d@x.com" % i, "c", a, "2025-01-01"] for i, a in enumerate(amounts)]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["1234567.89", "7.00", "0.00", "3.50", "-0.46", "100.00"]


def test_all_rows_invalid(tmp_path):
    rows = [HEADER_ROW, ["x", "", "c", "1", "2025-01-01"], ["y", "nope", "c", "1", "2025-01-01"]]
    assert run(tmp_path, rows) == [HEADER_ROW]
''',
        "packages": [],
    })

    return tasks


# ----------------------------------------------------------------------------
# Writing task folders
# ----------------------------------------------------------------------------

def write_text(path, text):
    """Always write with Linux line endings (\\n), even on Windows. Bash scripts break with \\r\\n."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))


PINNED_VERSIONS = {
    "pytest": "9.2.0",
    "flask": "3.1.3",
}


def dockerfile_for(task):
    lines = ["FROM python:3.12-slim", "WORKDIR /app"]
    if task.get("sql"):
        lines.append("RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 && rm -rf /var/lib/apt/lists/*")
    pip = [
        "%s==%s" % (pkg, PINNED_VERSIONS[pkg]) if pkg in PINNED_VERSIONS else pkg
        for pkg in ["pytest"] + task["packages"]
    ]
    lines.append("RUN pip install --no-cache-dir " + " ".join(pip))
    lines.append("COPY " + " ".join(sorted(task["starter"])) + " /app/")
    if task.get("sql"):
        lines.append("RUN python setup_db.py && rm setup_db.py")
    return "\n".join(lines) + "\n"


def solve_sh(task):
    out = ["#!/bin/bash", "set -e", ""]
    for name, content in task["solution"].items():
        out.append("cat > /app/%s << 'SOLUTION_EOF'" % name)
        out.append(content.rstrip("\n"))
        out.append("SOLUTION_EOF")
        out.append("")
    return "\n".join(out)


FALLBACK_TOML = '''schema_version = "1.4"
artifacts = []

[task]
name = "{name}"
version = "1.0.0"
description = ""
authors = []
keywords = []

[metadata]

[verifier]
timeout_sec = 600.0
environment_mode = "separate"
collect = []

[verifier.env]

[agent]
timeout_sec = 600.0

[environment]
network_mode = "public"
build_timeout_sec = 600.0
os = "linux"
mcp_servers = []

[environment.env]

[solution.env]
'''


def toml_for(task, template_text):
    name = "%s/%s" % (ORG, task["id"])
    if template_text is None:
        return FALLBACK_TOML.format(name=name)
    if re.search(r'(?m)^name\s*=\s*".*"\s*$', template_text):
        return re.sub(r'(?m)^name\s*=\s*".*"\s*$', 'name = "%s"' % name, template_text, count=1)
    return template_text


def write_task(task, out_dir, template_text):
    folder = out_dir / task["id"]
    if folder.exists():
        shutil.rmtree(folder)
    write_text(folder / "task.toml", toml_for(task, template_text))
    write_text(folder / "instruction.md", task["instruction"].strip() + "\n")
    write_text(folder / "environment" / "Dockerfile", dockerfile_for(task))
    for name, content in task["starter"].items():
        write_text(folder / "environment" / name, content)
    write_text(folder / "solution" / "solve.sh", solve_sh(task))
    write_text(folder / "tests" / "test.sh", TEST_SH)
    write_text(folder / "tests" / "test_outputs.py", task["tests"])


# ----------------------------------------------------------------------------
# Local check (no Docker)
# ----------------------------------------------------------------------------

def run_pytest(workdir, test_file):
    env = dict(os.environ, APP_DIR=str(workdir))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_file)],
        cwd=str(workdir), env=env, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def prepare_workdir(task, files):
    work = Path(tempfile.mkdtemp(prefix="codebench_"))
    for name, content in files.items():
        write_text(work / name, content)
    if "setup_db.py" in files:
        env = dict(os.environ, APP_DIR=str(work))
        subprocess.run([sys.executable, str(work / "setup_db.py")], cwd=str(work), env=env, check=True)
        (work / "setup_db.py").unlink()
    return work


def check_task(task, verbose=False):
    test_dir = Path(tempfile.mkdtemp(prefix="codebench_tests_"))
    test_file = test_dir / "test_outputs.py"
    write_text(test_file, task["tests"])

    work = prepare_workdir(task, task["starter"])
    code_start, out_start = run_pytest(work, test_file)
    shutil.rmtree(work, ignore_errors=True)

    solution_files = dict(task["starter"])
    solution_files.update(task["solution"])
    work = prepare_workdir(task, solution_files)
    code_solution, out_solution = run_pytest(work, test_file)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(test_dir, ignore_errors=True)

    starter_fails = code_start != 0
    solution_passes = code_solution == 0
    ok = starter_fails and solution_passes
    print("%-28s starter fails: %-3s  solution passes: %-3s  -> %s" % (
        task["id"], "yes" if starter_fails else "NO", "yes" if solution_passes else "NO", "OK" if ok else "PROBLEM"))
    if verbose or not ok:
        if not solution_passes:
            print("---- solution output ----\n" + out_solution)
        if not starter_fails:
            print("---- starter output (it should have failed) ----\n" + out_start)
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="test every task locally (needs pytest and flask)")
    parser.add_argument("--only", help="only this task id")
    parser.add_argument("--out", default="tasks", help="output folder (default: tasks)")
    parser.add_argument("--template", help="a task.toml made by `harbor init` to copy settings from")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    tasks = build_tasks()
    if args.only:
        tasks = [t for t in tasks if t["id"] == args.only]
        if not tasks:
            sys.exit("No task with id %r" % args.only)

    if args.check:
        results = [check_task(t, args.verbose) for t in tasks]
        print("\n%d of %d tasks OK" % (sum(results), len(results)))
        sys.exit(0 if all(results) else 1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use the task.toml that `harbor init` made as the template, if there is one.
    template_text = None
    candidates = [Path(args.template)] if args.template else []
    candidates += sorted(out_dir.glob("*/task.toml"))
    for candidate in candidates:
        if candidate.exists():
            template_text = candidate.read_text(encoding="utf-8")
            print("Using task.toml template from:", candidate)
            break
    if template_text is None:
        print("No task.toml template found - writing a basic task.toml (see the note in the guide).")

    for task in tasks:
        write_task(task, out_dir, template_text)
        print("wrote", out_dir / task["id"])

    meta = [{"id": t["id"], "type": t["type"], "difficulty": t["difficulty"]} for t in build_tasks()]
    write_text(Path("tasks_metadata.json"), json.dumps(meta, indent=2) + "\n")
    write_text(Path(".gitattributes"), "*.sh text eol=lf\nDockerfile text eol=lf\n*.toml text eol=lf\n")
    print("\nDone: %d tasks in %s/ (plus tasks_metadata.json and .gitattributes)" % (len(tasks), out_dir))


if __name__ == "__main__":
    main()