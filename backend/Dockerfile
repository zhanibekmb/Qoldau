FROM python:3.12-slim
WORKDIR /app
# DejaVu fonts give PDF reports Kazakh / Russian glyphs (US17).
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Migrate + seed on first start (seed is a no-op when data exists), then serve.
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
