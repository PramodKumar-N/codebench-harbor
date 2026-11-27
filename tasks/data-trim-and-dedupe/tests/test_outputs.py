import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
import csv

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
