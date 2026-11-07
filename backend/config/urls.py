# WRITTEN, NOT RUN
from django.http import JsonResponse
from django.urls import path


def live(_request):
    return JsonResponse({"status": "ok"})


def ready(_request):
    from django.db import connection
    try:
        connection.ensure_connection()
    except Exception:  # noqa: BLE001
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [path("api/v1/health/live", live), path("api/v1/health/ready", ready)]
