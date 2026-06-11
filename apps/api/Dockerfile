FROM python:3.12-slim

# System deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Mirror local path depth so config.py parents[4] resolves to /app (REPO_ROOT)
WORKDIR /app/apps/api

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

# Create REPO_ROOT-relative directories expected at startup
RUN mkdir -p /app/uploads /app/data

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
