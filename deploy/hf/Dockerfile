# Hugging Face Space (Docker SDK) image. The workflow .github/workflows/deploy-hf.yml stages: backend/, the OpenAPI file, this Dockerfile and README.md.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -m -u 1000 user
WORKDIR /app/backend
COPY --chown=user backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user backend/ .
COPY --chown=user docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml /app/docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml
USER user
EXPOSE 7860
# Settings come ONLY from the Space's Secrets/Variables (no secret in the image). Migrate, then serve on the port Spaces expects.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application -b 0.0.0.0:7860 --workers 2 --timeout 60"]
