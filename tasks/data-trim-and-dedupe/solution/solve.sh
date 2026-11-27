#!/bin/bash
set -e

cat > /app/clean.py << 'SOLUTION_EOF'
import csv


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    email_index = header.index("email") if "email" in header else 0
    seen = set()
    cleaned = []
    for row in rows:
        row = [value.strip() for value in row]
        if len(row) <= email_index or not row[email_index]:
            continue
        key = tuple(row)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
SOLUTION_EOF
