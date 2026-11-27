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
