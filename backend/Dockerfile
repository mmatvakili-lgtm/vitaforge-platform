FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --system --no-create-home vitaforge && chown -R vitaforge /app
USER vitaforge
EXPOSE 8000
# Overridden by docker-compose (migrate first). Settings come ONLY from environment variables; no secret is baked into the image.
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000", "--workers", "3"]
