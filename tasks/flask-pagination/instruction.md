The file /app/app.py is a Flask API with GET /items that returns a list of
25 items with pagination. It is buggy. Fix it so that:

- pages start at 1 (page=1 is the first page); the defaults are page=1 and per_page=10
- the JSON response has exactly these keys:
  page, per_page, total, total_pages, items
- total is the number of all items (25); total_pages is the number of pages needed
  (for example 3 when per_page=10)
- a page after the last one returns status 200 with "items": []
- page must be an integer >= 1, and per_page must be an integer from 1 to 50;
  anything else (0, -1, abc, 1.5, 51 ...) returns status 400 and {"error": "invalid pagination"}
