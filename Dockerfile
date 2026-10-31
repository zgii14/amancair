# Backend AmanCair untuk Railway. Konteks build = root repo,
# supaya draf contoh di workbuddy-spj/ ikut masuk image untuk demo online.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

COPY backend/profil ./profil
COPY backend/seed ./seed
COPY workbuddy-spj/keluar/draf ./demo-draf

ENV DATA_DIR=/data \
    SPJ_DRAF_ROOT=/data/draf \
    SPJ_DRAF_CONTOH=/app/demo-draf \
    SPJ_SIAP_ROOT=/data/siap-cair \
    SPJ_SEED_FILE=/app/seed/spj_demo.json

CMD ["sh", "-c", "uvicorn app.api:app_dari_env --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
