import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
from app import find_max


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
