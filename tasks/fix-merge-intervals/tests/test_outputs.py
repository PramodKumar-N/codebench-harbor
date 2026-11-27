import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
import copy

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
