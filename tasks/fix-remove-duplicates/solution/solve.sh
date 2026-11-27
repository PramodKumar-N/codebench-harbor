#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
def remove_duplicates(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
SOLUTION_EOF
