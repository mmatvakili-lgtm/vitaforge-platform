"""Pure routing decision for config.wsgi (testable without Django)."""
DJANGO_PATHS = ("/api/v1/health/live", "/api/v1/health/ready")      # exact paths only: /api/v1/health/* also contains real API operations


def goes_to_api(path: str, dev_content: bool) -> bool:
    if path in DJANGO_PATHS or path in tuple(p + "/" for p in DJANGO_PATHS):
        return False
    return path.startswith("/api/v1/") or (path == "/" and dev_content)
