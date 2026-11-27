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
