#!/bin/bash
set -e

cat > /app/clean.py << 'SOLUTION_EOF'
import csv
from datetime import datetime

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]


def normalize_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def normalize_phone(text):
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else ""


def clean_csv(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        rows = list(reader)
    index = {name: i for i, name in enumerate(header)}
    cleaned = []
    for row in rows:
        row = [value.strip() for value in row]
        row += [""] * (len(header) - len(row))
        row[index["name"]] = " ".join(row[index["name"]].split()).title()
        row[index["email"]] = row[index["email"]].lower()
        row[index["phone"]] = normalize_phone(row[index["phone"]])
        row[index["joined"]] = normalize_date(row[index["joined"]])
        cleaned.append(row)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)
SOLUTION_EOF
