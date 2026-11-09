"""Environment validation (AC-OPS-002). Pure Python so it is testable without Django."""
from __future__ import annotations

from typing import Mapping

REQUIRED = ("DJANGO_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "ALLOWED_HOSTS")
DUMMY_MARKERS = ("change-me", "dummy", "example")


class ConfigError(Exception):
    pass


def _bool(v: str | None, default=False) -> bool:
    return default if v is None else v.strip().lower() in ("1", "true", "yes")


def load_dotenv(path, environ) -> None:
    """Minimal .env reader (KEY=VALUE, # comments). Real environment variables win over the file."""
    import pathlib
    p = pathlib.Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(env: Mapping[str, str]) -> dict:
    missing = [k for k in REQUIRED if not env.get(k)]
    if missing:
        raise ConfigError("missing: " + ",".join(missing))
    cfg = {"secret_key": env["DJANGO_SECRET_KEY"], "debug": _bool(env.get("DJANGO_DEBUG")),
           "database_url": env["DATABASE_URL"], "redis_url": env["REDIS_URL"],
           "allowed_hosts": [h.strip() for h in env["ALLOWED_HOSTS"].split(",") if h.strip()],
           "ai_external_health_data": _bool(env.get("AI_EXTERNAL_HEALTH_DATA")),
           "offline_workout_log": _bool(env.get("FEATURE_OFFLINE_WORKOUT_LOG")),
           "clinical_content_published": _bool(env.get("CLINICAL_CONTENT_PUBLISHED")),
           "dev_content": _bool(env.get("VITAFORGE_DEV_CONTENT"))}
    if cfg["dev_content"] and not cfg["debug"]:
        raise ConfigError("VITAFORGE_DEV_CONTENT (experimental sample content) is only allowed with DJANGO_DEBUG=true")
    if cfg["ai_external_health_data"]:
        raise ConfigError("AI_EXTERNAL_HEALTH_DATA must be false until legal review (OPEN-002/EXP-012)")
    if not cfg["debug"]:
        if any(m in cfg["secret_key"].lower() for m in DUMMY_MARKERS) or len(cfg["secret_key"]) < 32:
            raise ConfigError("production requires a real DJANGO_SECRET_KEY (>=32 chars)")
        if "*" in cfg["allowed_hosts"]:
            raise ConfigError("wildcard ALLOWED_HOSTS forbidden in production")
    return cfg
