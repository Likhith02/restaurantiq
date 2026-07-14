# RestaurantIQ — production image.
# Build:  docker build -t restaurantiq .
# Run:    docker run -p 8010:8010 restaurantiq
FROM python:3.12-slim

# Don't write .pyc files; flush logs immediately so `docker logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/restaurantiq

# Install dependencies first so Docker caches this layer between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY frontend ./frontend

# Run as a non-root user; SQLite fallback needs a writable data dir.
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown appuser /data
USER appuser
ENV RIQ_DB_PATH=/data/restaurantiq.db

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8010)}/api/health')"

# Render injects $PORT; default to 8010 for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8010}"]
