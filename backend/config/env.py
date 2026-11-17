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
           "dev_content": _bool(env.get("VITAFORGE_DEV_CONTENT")), "content_mode": "reviewed"}
    if cfg["debug"] and env.get("VITAFORGE_DEV_CONTENT") is None:
        # Local/test runs must never dead-end on the "no reviewed content" gate: with DJANGO_DEBUG=true the sample catalogue
        # (labelled experimental, with warnings) is the default. Set VITAFORGE_DEV_CONTENT=false to test the strict posture.
        cfg["dev_content"] = True
    from mailer.config import MailConfigError, load_mail_config
    from tgverify.config import TelegramConfigError, load_telegram_config
    try:
        cfg["telegram"] = load_telegram_config(env, cfg["debug"])
        # e-mail is optional when Telegram (the primary channel) is live; otherwise production still requires SMTP
        cfg["mail"] = load_mail_config(env, cfg["debug"], allow_disabled=cfg["telegram"]["provider"] == "live")
    except (MailConfigError, TelegramConfigError) as e:
        raise ConfigError(str(e))
    if cfg["dev_content"] and not cfg["debug"]:
        raise ConfigError("VITAFORGE_DEV_CONTENT (experimental sample content) is only allowed with DJANGO_DEBUG=true")
    mode = (env.get("VITAFORGE_CONTENT_MODE") or "reviewed").strip().lower()
    if mode not in ("reviewed", "ai_curated_demo"):
        raise ConfigError("VITAFORGE_CONTENT_MODE must be 'reviewed' or 'ai_curated_demo'")
    if mode == "ai_curated_demo":
        # Public demo / portfolio mode: AI-curated, NOT expert-reviewed content. Requires an explicit acknowledgement so it can never be enabled by accident.
        if (env.get("VITAFORGE_ACK_AI_CURATED_CONTENT") or "").strip().lower() != "yes":
            raise ConfigError("VITAFORGE_CONTENT_MODE=ai_curated_demo requires VITAFORGE_ACK_AI_CURATED_CONTENT=yes (content is not expert-reviewed)")
        cfg["content_mode"], cfg["dev_content"] = mode, True
    # Advisory posture (DEC-ADVISORY): refer-and-warn but still produce plans. Only with demo/test content; default on there, never in production.
    adv = env.get("VITAFORGE_ADVISORY")
    cfg["advisory"] = cfg["dev_content"] if adv is None else _bool(adv)
    if cfg["advisory"] and not cfg["dev_content"]:
        raise ConfigError("VITAFORGE_ADVISORY is only allowed with demo/test content (DJANGO_DEBUG=true or ai_curated_demo)")
    if cfg["ai_external_health_data"]:
        raise ConfigError("AI_EXTERNAL_HEALTH_DATA must be false until legal review (OPEN-002/EXP-012)")
    if not cfg["debug"]:
        if any(m in cfg["secret_key"].lower() for m in DUMMY_MARKERS) or len(cfg["secret_key"]) < 32:
            raise ConfigError("production requires a real DJANGO_SECRET_KEY (>=32 chars)")
        if "*" in cfg["allowed_hosts"]:
            raise ConfigError("wildcard ALLOWED_HOSTS forbidden in production")
    return cfg


def tune_database(db: dict) -> dict:
    """SQLite (local/demo runs) under Django's threaded server: the default deferred transactions deadlock into "database is locked" (HTTP 500)
    when two requests write at once (e.g. the first page load seeding the catalogue while other calls arrive). IMMEDIATE transactions make
    writers queue instead, WAL lets readers proceed, and a long busy timeout absorbs bursts. PostgreSQL configs are returned unchanged."""
    if "sqlite" not in str(db.get("ENGINE", "")):
        return db
    opts = dict(db.get("OPTIONS") or {})
    opts.setdefault("transaction_mode", "IMMEDIATE")
    opts.setdefault("timeout", 30)
    opts.setdefault("init_command", "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
    return {**db, "OPTIONS": opts}
