FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY database/init.sql ./init.sql
COPY database/railway_seed.sql ./railway_seed.sql

EXPOSE 5000

CMD ["sh", "-c", "python bootstrap_db.py && exec gunicorn --bind 0.0.0.0:${BACKEND_PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --access-logfile - --error-logfile - app:app"]
