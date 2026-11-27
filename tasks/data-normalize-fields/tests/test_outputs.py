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


HEADER_ROW = ["name", "email", "phone", "joined"]


def test_all_rules(tmp_path):
    rows = [
        HEADER_ROW,
        ["  asha   rao ", "ASHA@Example.COM", "+91 98441-42846", "05-Nov-2025"],
        ["BALA kumar", "bala@x.com", "12345", "31/12/2025"],
        ["chitra iyer", "c@x.com", "080 2345 6789", "2025-02-30"],
        ["Dev Patel", " d@x.com ", "(022) 4000-1234", "15/13/2025"],
        ["esha gupta", "e@x.com", "9876543210", "2024-07-04"],
    ]
    assert run(tmp_path, rows) == [
        HEADER_ROW,
        ["Asha Rao", "asha@example.com", "9844142846", "2025-11-05"],
        ["Bala Kumar", "bala@x.com", "", "2025-12-31"],
        ["Chitra Iyer", "c@x.com", "8023456789", ""],
        ["Dev Patel", "d@x.com", "2240001234", ""],
        ["Esha Gupta", "e@x.com", "9876543210", "2024-07-04"],
    ]


def test_dates_in_all_three_formats(tmp_path):
    rows = [
        HEADER_ROW,
        ["a", "a@x.com", "1111111111", "2025-01-09"],
        ["b", "b@x.com", "1111111111", "09/01/2025"],
        ["c", "c@x.com", "1111111111", "09-Jan-2025"],
        ["d", "d@x.com", "1111111111", "January 9, 2025"],
        ["e", "e@x.com", "1111111111", ""],
    ]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["2025-01-09", "2025-01-09", "2025-01-09", "", ""]


def test_leap_day(tmp_path):
    rows = [HEADER_ROW, ["a", "a@x.com", "1111111111", "29/02/2024"],
            ["b", "b@x.com", "1111111111", "29/02/2025"]]
    result = run(tmp_path, rows)
    assert [r[3] for r in result[1:]] == ["2024-02-29", ""]


def test_every_row_is_kept_in_order(tmp_path):
    rows = [HEADER_ROW] + [["n%d" % i, "e%d@x.com" % i, "", ""] for i in range(5)]
    result = run(tmp_path, rows)
    assert [r[1] for r in result[1:]] == ["e%d@x.com" % i for i in range(5)]
