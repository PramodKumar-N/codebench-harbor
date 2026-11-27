The file /app/app.py is a small Flask API with two routes:
POST /users and GET /users. The POST route is buggy. Fix it so that:

- a valid request {"name": "Asha"} returns status 201 and the JSON {"id": 1, "name": "Asha"}
  (ids go 1, 2, 3 ...)
- the name is trimmed: "  Asha " is saved as "Asha"
- a missing name, an empty name, a name with only spaces, a name that is not a string,
  or a request with no JSON body returns status 400 and the JSON {"error": "name is required"}
- GET /users keeps returning the list of saved users
