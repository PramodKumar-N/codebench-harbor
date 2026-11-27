#!/bin/bash
set -e

cat > /app/clean.py << 'SOLUTION_EOF'
import csv
import math


def clean_amount(text):
    text = text.replace("$", "").replace(",", "").strip()
    try:
        value = float(text)
    except ValueError:
        return "0.00"
    if not math.isfinite(value):
        return "0.00"
    return "%.2f" % value


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    index = {name: i for i, name in enumerate(header)}
    best = {}
    for row in rows:
        row = [value.strip() for value in row]
        row += [""] * (len(header) - len(row))
        email = row[index["email"]].lower()
        if not email or "@" not in email:
            continue
        row[index["email"]] = email
        if email not in best or row[index["updated"]] >= best[email][index["updated"]]:
            best[email] = row
    cleaned = []
    for email in sorted(best):
        row = best[email]
        if not row[index["city"]]:
            row[index["city"]] = "Unknown"
        row[index["amount"]] = clean_amount(row[index["amount"]])
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
SOLUTION_EOF
