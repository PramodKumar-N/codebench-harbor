#!/bin/bash
set -e

cat > /app/query.sql << 'SOLUTION_EOF'
WITH totals AS (
    SELECT c.city AS city, c.name AS name, SUM(o.amount) AS total_spent
    FROM customers c
    JOIN orders o ON o.customer_id = c.id
    GROUP BY c.id, c.city, c.name
)
SELECT city, name, total_spent
FROM totals t
WHERE total_spent = (SELECT MAX(total_spent) FROM totals WHERE city = t.city)
ORDER BY city;
SOLUTION_EOF
