Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV with the header name,email,city,amount,updated and writes a cleaned
CSV (with the same header) to output_path. A small example is in /app/sample_messy.csv.

Rules, in this order:
1. remove spaces at both ends of every value
2. email: make it lowercase; remove rows whose email is empty or has no "@"
3. the same email can appear several times (compare after lowercasing). Keep only ONE row
   per email: the one with the latest `updated` date (dates are YYYY-MM-DD text).
   If two rows have the same date, keep the one that appears LATER in the file.
   The kept row's own values are used (do not mix values from different rows).
4. city: if empty, write "Unknown"
5. amount: remove "$" and "," characters, then write it with exactly 2 decimals
   ("$1,200.5" -> "1200.50", "-12.5" -> "-12.50"). If it is empty or not a number
   (for example "abc" or "nan"), write "0.00".
6. sort the final rows by email, A to Z
