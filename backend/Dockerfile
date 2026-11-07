# WRITTEN, NOT RUN
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && chown -R app /app
USER app
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000"]
