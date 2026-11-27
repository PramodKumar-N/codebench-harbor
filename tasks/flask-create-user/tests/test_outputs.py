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
