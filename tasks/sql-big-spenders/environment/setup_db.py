import os
import sqlite3

path = os.path.join(os.environ.get("APP_DIR", "/app"), "shop.db")
if os.path.exists(path):
    os.remove(path)
con = sqlite3.connect(path)
con.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER, order_date TEXT);
""")
con.executemany("INSERT INTO customers VALUES (?, ?, ?)", [(1, 'Asha Rao', 'Bengaluru'), (2, 'Bala Kumar', 'Chennai'), (3, 'Chitra Iyer', 'Bengaluru'), (4, 'Dev Patel', 'Mumbai'), (5, 'Esha Gupta', 'Mumbai'), (6, 'Farhan Ali', 'Chennai'), (7, 'Gita Nair', 'Kochi'), (8, 'Hari Singh', 'Bengaluru')])
con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", [(1, 1, 3000, '2025-01-10'), (2, 1, 2500, '2025-02-15'), (3, 2, 1200, '2025-01-20'), (4, 3, 5200, '2025-03-05'), (5, 4, 800, '2025-01-25'), (6, 4, 4500, '2025-02-28'), (7, 2, 300, '2025-03-15'), (8, 1, 700, '2025-04-02'), (9, 5, 6000, '2025-04-10'), (10, 3, 150, '2025-04-20'), (11, 6, 2200, '2025-02-05'), (12, 6, 2900, '2025-03-25'), (13, 4, 1000, '2025-05-01'), (14, 5, 100, '2025-05-05'), (15, 2, 4000, '2025-05-20'), (16, 1, 50, '2025-06-01')])
con.commit()
con.close()
