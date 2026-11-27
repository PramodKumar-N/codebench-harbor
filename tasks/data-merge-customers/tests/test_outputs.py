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


HEADER_ROW = ["name", "email", "city", "amount", "updated"]


def test_full_example(tmp_path):
    rows = [
        HEADER_ROW,
        ["Asha", "ASHA@x.com", "Bengaluru", "$1,200.50", "2025-01-10"],
        ["Asha R", "asha@x.com ", "", "$1,500", "2025-03-01"],
        ["Bala", "bala@x.com", "Chennai", "abc", "2025-02-01"],
        ["NoEmail", "", "Pune", "10", "2025-01-01"],
        ["BadEmail", "not-an-email", "Pune", "10", "2025-01-01"],
        ["Chitra", "chitra@x.com", "Mumbai", "-12.5", "2025-05-05"],
        ["Chitra Old", "chitra@x.com", "Delhi", "99", "2025-05-05"],
        ["Dev", "dev@x.com", "Goa", "", "2025-04-04"],
    ]
    assert run(tmp_path, rows) == [
        HEADER_ROW,
        ["Asha R", "asha@x.com", "Unknown", "1500.00", "2025-03-01"],
        ["Bala", "bala@x.com", "Chennai", "0.00", "2025-02-01"],
        ["Chitra Old", "chitra@x.com", "Delhi", "99.00", "2025-05-05"],
        ["Dev", "dev@x.com", "Goa", "0.00", "2025-04-04"],
    ]


def test_latest_date_wins_even_if_it_comes_first(tmp_path):
    rows = [
        HEADER_ROW,
        ["New", "a@x.com", "Pune", "5", "2025-06-01"],
        ["Old", "A@x.com", "Goa", "9", "2025-01-01"],
    ]
    assert run(tmp_path, rows) == [HEADER_ROW, ["New", "a@x.com", "Pune", "5.00", "2025-06-01"]]


def test_rows_are_sorted_by_email(tmp_path):
    rows = [
        HEADER_ROW,
        ["Z", "z@x.com", "c", "1", "2025-01-01"],
        ["A", "a@x.com", "c", "1", "2025-01-01"],
        ["M", "m@x.com", "c", "1", "2025-01-01"],
    ]
    result = run(tmp_path, rows)
    assert [r[1] for r in result[1:]] == ["a@x.com", "m@x.com", "z@x.com"]


def test_amount_formats(tmp_path):
    amounts = ["$1,234,567.891", "7", "nan", "  $ 3.5 ", "-0.456", "1e2"]
    rows = [HEADER_ROW] + [["n", "u%d@x.com" % i, "c", a, "2025-01-01"] for i, a in enumerate(amounts)]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["1234567.89", "7.00", "0.00", "3.50", "-0.46", "100.00"]


def test_all_rows_invalid(tmp_path):
    rows = [HEADER_ROW, ["x", "", "c", "1", "2025-01-01"], ["y", "nope", "c", "1", "2025-01-01"]]
    assert run(tmp_path, rows) == [HEADER_ROW]
