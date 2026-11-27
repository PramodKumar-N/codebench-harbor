The SQLite database is at /app/shop.db. It has two tables:

- customers(id, name, city)
- orders(id, customer_id, amount, order_date)

`amount` is a whole number (rupees). `order_date` is text like 2025-03-05.
`orders.customer_id` points to `customers.id`.

Write your answer as ONE SELECT query in the file /app/query.sql.
Use exactly the column names (aliases) and the ordering given below.
Do not change the database.

Task: for each city, find the customer with the highest TOTAL order amount.
Only customers with at least one order count, and a city with no orders at all
does not appear. Show the city, the customer name and the total.
Sort by city (A to Z). (There are no ties in this data.)

Required columns, in this order: city, name, total_spent.
