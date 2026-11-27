import os
import sys

APP = os.environ.get("APP_DIR", "/app")
sys.path.insert(0, APP)
import sqlite3


def run_query():
    with open(os.path.join(APP, "query.sql"), encoding="utf-8") as f:
        sql = f.read()
    con = sqlite3.connect(os.path.join(APP, "shop.db"))
    con.execute("PRAGMA query_only = ON")
    # the database must be untouched
    assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 16
    assert con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 8
    cur = con.execute(sql)
    assert cur.description is not None, "query.sql must contain one SELECT query"
    columns = [d[0] for d in cur.description]
    rows = [tuple(r) for r in cur.fetchall()]
    return columns, rows


def test_columns():
    columns, _ = run_query()
    assert columns == ['name', 'total_spent']


def test_rows_and_order():
    _, rows = run_query()
    assert rows == [('Dev Patel', 6300), ('Asha Rao', 6250), ('Esha Gupta', 6100)]
