#!/bin/bash
set -e

cat > /app/app.py << 'SOLUTION_EOF'
def find_max(nums):
    if not nums:
        return None
    biggest = nums[0]
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
SOLUTION_EOF
