FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==9.2.0
COPY query.sql setup_db.py /app/
RUN python setup_db.py && rm setup_db.py
