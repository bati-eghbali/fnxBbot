# API image for Render. The index (data/chroma, data/bm25.pkl) is built locally and baked in,
# because the free tier's disk is wiped on every restart.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY config.py ./
COPY app/ app/
COPY ingest/__init__.py ingest/embed.py ingest/index.py ingest/tokenize_he.py ingest/
COPY data/chroma/ data/chroma/
COPY data/bm25.pkl data/

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
