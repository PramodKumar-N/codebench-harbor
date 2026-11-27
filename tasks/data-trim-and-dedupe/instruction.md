Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV file with the header name,email,city and writes a cleaned CSV
(also with a header) to output_path. A small example of the input format is in
/app/sample_messy.csv.

Cleaning rules:
1. remove spaces at the start and end of EVERY value
2. remove rows whose email is empty (after trimming)
3. remove duplicate rows: rows that are exactly the same after trimming
   (keep the first one; rows that differ in any column are NOT duplicates)
4. keep the original row order and the same header
