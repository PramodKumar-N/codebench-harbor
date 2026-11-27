The SQLite database is at /app/shop.db. It has two tables:

- customers(id, name, city)
- orders(id, customer_id, amount, order_date)

`amount` is a whole number (rupees). `order_date` is text like 2025-03-05.
`orders.customer_id` points to `customers.id`.

Write your answer as ONE SELECT query in the file /app/query.sql.
Use exactly the column names (aliases) and the ordering given below.
Do not change the database.

Task: find the customers who have never placed any order.
Sort by name (A to Z).

Required columns, in this order: name, city.
