#!/bin/bash
set -e

cat > /app/query.sql << 'SOLUTION_EOF'
SELECT c.name AS name, SUM(o.amount) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name
HAVING SUM(o.amount) > 5500
ORDER BY total_spent DESC;
SOLUTION_EOF
