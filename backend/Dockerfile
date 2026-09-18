FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libexpat dibutuhkan oleh wheel rasterio (pembacaan DEM GeoTIFF).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY database/init.sql ./init.sql
COPY database/railway_seed.sql ./railway_seed.sql

EXPOSE 5000

CMD ["sh", "-c", "PORT=${PORT:-${BACKEND_PORT:-5000}}; python bootstrap_db.py && exec gunicorn --bind [::]:${PORT} --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile - app:app"]
