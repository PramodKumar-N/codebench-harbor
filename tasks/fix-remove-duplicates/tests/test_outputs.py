import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
from app import remove_duplicates


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
