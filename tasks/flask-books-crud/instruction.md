The file /app/app.py is a small in-memory "books" API. Several routes are
buggy or incomplete. Make it follow these rules. Errors are always JSON:
{"error": "<message>"} (any message text is fine).

POST /books  body {"title": ..., "author": ...}
- title is required and must be a non-empty string (spaces only does not count) -> else 400
- author is optional (default ""), but if given it must be a string -> else 400
- title and author are trimmed
- a book with the same title AND same author (ignoring upper/lower case) already exists -> 409
  (same title with a different author is allowed)
- success: 201 and {"id", "title", "author"}; ids start at 1 and are never reused

GET /books
- returns all books as a list sorted by id
- optional ?author=NAME returns only books by that author (ignoring case)

GET /books/<id>   -> the book, or 404 if it does not exist

PUT /books/<id>
- only "title" and "author" can be changed, and only the fields that are sent
  (a partial update keeps the other fields); "id" can never change
- title, if sent, must be a non-empty string -> else 400
- 404 if the book does not exist; success returns 200 and the updated book

DELETE /books/<id>  -> 204 with no body, or 404 if it does not exist
