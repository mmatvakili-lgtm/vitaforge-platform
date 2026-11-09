# NEEDS LOCAL VERIFICATION: written without a Django runtime (see docs/WINDOWS_SETUP.md).
import os
import pathlib

from .env import load_config, load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env", os.environ)
load_dotenv(BASE_DIR / ".env", os.environ)

CFG = load_config(os.environ)
SECRET_KEY = CFG["secret_key"]
DEBUG = CFG["debug"]
ALLOWED_HOSTS = CFG["allowed_hosts"]
INSTALLED_APPS = ["apps.core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": __import__("dj_database_url").parse(CFG["database_url"], conn_max_age=60)}
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "fa"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 0 if CFG["debug"] else 31536000
# The API (/api/v1/*) owns its cookies (ADR-0009: `sessionid` + `csrftoken`, set by the application with HttpOnly/Secure rules).
CELERY_BROKER_URL = CFG["redis_url"]                  # reserved for background jobs; no Celery task exists yet
CLINICAL_CONTENT_PUBLISHED = CFG["clinical_content_published"]
