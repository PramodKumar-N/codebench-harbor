import sys
sys.path.insert(0, "/app")
from app import find_max

def test_normal():
    assert find_max([3, 9, 2]) == 9

def test_negatives():
    assert find_max([-5, -1, -8]) == -1

def test_empty():
    assert find_max([]) is None