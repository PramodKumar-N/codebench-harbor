#!/bin/bash
set -e

cat > /app/query.sql << 'SOLUTION_EOF'
SELECT c.city AS city, COUNT(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.city
ORDER BY order_count DESC, city ASC;
SOLUTION_EOF
