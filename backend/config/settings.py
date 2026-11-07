# WRITTEN, NOT RUN: Django is not installable in the build environment (ADR-0007).
import os

from .env import load_config

CFG = load_config(os.environ)
SECRET_KEY = CFG["secret_key"]
DEBUG = CFG["debug"]
ALLOWED_HOSTS = CFG["allowed_hosts"]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "rest_framework", "apps.core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
AUTH_USER_MODEL = "core.User"
DATABASES = {"default": __import__("dj_database_url").parse(CFG["database_url"])}
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "fa"
DEFAULT_AUTO_FIELD = "django.db.models.UUIDField"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = CFG["debug"] is False
CSRF_COOKIE_SECURE = CFG["debug"] is False
SECURE_HSTS_SECONDS = 0 if CFG["debug"] else 31536000
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.auth.BearerTokenAuthentication"],
                  "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}
CELERY_BROKER_URL = CFG["redis_url"]
CLINICAL_CONTENT_PUBLISHED = CFG["clinical_content_published"]
