Write the function clean_csv(input_path, output_path) in /app/clean.py.
It reads a CSV with the header name,email,phone,joined and writes a cleaned CSV
(with the same header) to output_path. Every row is kept, in the same order.
A small example of the input is in /app/sample_messy.csv.

Rules for each value (first remove spaces at both ends):
- name: make each word start with a capital letter and the rest lowercase, and
  replace repeated inner spaces with one space ("  asha   RAO " -> "Asha Rao")
- email: lowercase
- phone: keep only the digits. If there are more than 10 digits keep the LAST 10.
  If there are fewer than 10 digits, the result is an empty value.
- joined: convert to the ISO format YYYY-MM-DD. The input can be written as
  YYYY-MM-DD, DD/MM/YYYY or DD-Mon-YYYY (for example 05-Nov-2025).
  Anything else, or a date that does not exist (for example 31/02/2025), becomes an empty value.
