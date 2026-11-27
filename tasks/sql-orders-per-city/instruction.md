The SQLite database is at /app/shop.db. It has two tables:

- customers(id, name, city)
- orders(id, customer_id, amount, order_date)

`amount` is a whole number (rupees). `order_date` is text like 2025-03-05.
`orders.customer_id` points to `customers.id`.

Write your answer as ONE SELECT query in the file /app/query.sql.
Use exactly the column names (aliases) and the ordering given below.
Do not change the database.

Task: count how many orders were placed by customers of each city.
EVERY city that has at least one customer must appear, even if its count is 0.
Sort by order_count (highest first), then by city (A to Z).

Required columns, in this order: city, order_count.
