import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
import importlib


def make_client():
    """Fresh copy of the app (empty data) for every test."""
    import app as module
    importlib.reload(module)
    return module.app.test_client()


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
