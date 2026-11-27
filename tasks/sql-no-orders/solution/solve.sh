#!/bin/bash
set -e

cat > /app/query.sql << 'SOLUTION_EOF'
SELECT c.name AS name, c.city AS city
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL
ORDER BY c.name;
SOLUTION_EOF
