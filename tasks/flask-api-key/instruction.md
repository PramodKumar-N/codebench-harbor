The file /app/app.py is a Flask API with a public route (GET /public) and a
protected route (GET /secret). The protection is broken. Fix GET /secret so that:

- the header X-API-Key must equal "secret123"
- header missing or empty: status 401 and {"error": "missing api key"}
- header present but wrong: status 403 and {"error": "invalid api key"}
- header correct: status 200 and {"secret": "the cake is a lie"}
- the key comparison must be case-sensitive ("SECRET123" is wrong)

GET /public must stay open to everyone and keep working.
