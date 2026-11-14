# Build context is the REPOSITORY ROOT (the API reads the OpenAPI contract from docs/ at start-up):
#   docker build -f backend/Dockerfile -t vitaforge-api .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml /app/docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml
RUN useradd --system --no-create-home vitaforge && chown -R vitaforge /app
USER vitaforge
EXPOSE 8000
# Overridden by docker-compose (migrate first). Settings come ONLY from environment variables; no secret is baked into the image.
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000", "--workers", "3"]
