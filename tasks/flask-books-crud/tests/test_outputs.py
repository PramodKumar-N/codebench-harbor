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
