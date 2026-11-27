The file /app/app.py is a Flask API with a route GET /search?q=... that
searches a fixed list of items. It is buggy. Fix it so that:

- the search is case-insensitive and matches any part of the item text
  (q=pie finds "apple pie" and "Cherry Pie")
- results keep the original order and the original spelling of the items
- spaces around q are ignored (q=" banana " works like q=banana)
- if q is missing or empty, return status 200 and {"results": []}
- the response is always JSON in the form {"results": [...]}
