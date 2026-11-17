import pytest
from config.env import ConfigError, load_config

from .test_env import OK


def test_default_is_reviewed_only_and_plain_dev_flag_still_needs_debug():
    assert load_config(OK)["content_mode"] == "reviewed"
    with pytest.raises(ConfigError):
        load_config({**OK, "VITAFORGE_DEV_CONTENT": "true"})            # unchanged: sample content only with DJANGO_DEBUG=true


def test_ai_curated_demo_requires_explicit_acknowledgement():
    with pytest.raises(ConfigError):
        load_config({**OK, "VITAFORGE_CONTENT_MODE": "ai_curated_demo"})
    with pytest.raises(ConfigError):
        load_config({**OK, "VITAFORGE_CONTENT_MODE": "ai_curated_demo", "VITAFORGE_ACK_AI_CURATED_CONTENT": "true"})   # only the exact word "yes"
    c = load_config({**OK, "VITAFORGE_CONTENT_MODE": "ai_curated_demo", "VITAFORGE_ACK_AI_CURATED_CONTENT": "yes"})
    assert c["content_mode"] == "ai_curated_demo" and c["dev_content"] is True


def test_unknown_mode_rejected_and_other_production_rules_still_apply():
    with pytest.raises(ConfigError):
        load_config({**OK, "VITAFORGE_CONTENT_MODE": "yolo"})
    demo = {**OK, "VITAFORGE_CONTENT_MODE": "ai_curated_demo", "VITAFORGE_ACK_AI_CURATED_CONTENT": "yes"}
    for bad in ({"AI_EXTERNAL_HEALTH_DATA": "true"}, {"ALLOWED_HOSTS": "*"}, {"DJANGO_SECRET_KEY": "short"}):
        with pytest.raises(ConfigError):
            load_config({**demo, **bad})


def test_debug_defaults_to_sample_content_but_strict_can_be_forced():
    assert load_config({**OK, "DJANGO_DEBUG": "true"})["dev_content"] is True
    assert load_config({**OK, "DJANGO_DEBUG": "true", "VITAFORGE_DEV_CONTENT": "false"})["dev_content"] is False
    assert load_config({**OK, "DJANGO_DEBUG": "false"})["dev_content"] is False


def test_advisory_defaults_on_with_demo_content_and_is_refused_in_production():
    import pytest
    from config.env import ConfigError, load_config
    base = dict(OK)
    assert load_config({**base, "DJANGO_DEBUG": "true"})["advisory"] is True
    assert load_config({**base, "DJANGO_DEBUG": "true", "VITAFORGE_ADVISORY": "false"})["advisory"] is False
    with pytest.raises(ConfigError):
        load_config({**base, "VITAFORGE_ADVISORY": "true"})


def test_sqlite_is_tuned_for_concurrent_requests_and_postgres_untouched():
    from config.env import tune_database
    lite = tune_database({"ENGINE": "django.db.backends.sqlite3", "NAME": "x"})
    assert lite["OPTIONS"]["transaction_mode"] == "IMMEDIATE" and lite["OPTIONS"]["timeout"] >= 20 and "WAL" in lite["OPTIONS"]["init_command"]
    pg = {"ENGINE": "django.db.backends.postgresql", "NAME": "x"}
    assert tune_database(pg) == pg
