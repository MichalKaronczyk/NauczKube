# Naucz Kubę — jeden obraz: zbudowany frontend serwowany przez FastAPI.
# Budowanie i uruchomienie: docker compose up

# --- etap 1: frontend ------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# build trafia do ../backend/static, więc katalog musi istnieć
RUN mkdir -p /backend/static && npm run build -- --outDir /backend/static --emptyOutDir

# --- etap 2: backend -------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/catalog ./catalog
COPY --from=frontend /backend/static ./static

# aplikacja nie potrzebuje roota
RUN useradd --create-home --uid 10001 kuba && chown -R kuba:kuba /app
USER kuba

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
