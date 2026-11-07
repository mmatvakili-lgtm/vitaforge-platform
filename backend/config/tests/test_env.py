import pytest
from config.env import ConfigError, load_config

OK = {"DJANGO_SECRET_KEY": "k" * 40, "DATABASE_URL": "postgres://x", "REDIS_URL": "redis://x", "ALLOWED_HOSTS": "a.com"}


def test_ok_and_flags():
    c = load_config(OK)
    assert c["allowed_hosts"] == ["a.com"] and c["ai_external_health_data"] is False and c["clinical_content_published"] is False


@pytest.mark.parametrize("drop", list(OK))
def test_missing(drop):
    e = dict(OK); e.pop(drop)
    with pytest.raises(ConfigError):
        load_config(e)


@pytest.mark.parametrize("patch", [{"AI_EXTERNAL_HEALTH_DATA": "true"}, {"DJANGO_SECRET_KEY": "change-me-dummy" * 3},
                                   {"DJANGO_SECRET_KEY": "short"}, {"ALLOWED_HOSTS": "*"}])
def test_production_rules(patch):
    with pytest.raises(ConfigError):
        load_config({**OK, **patch})


def test_debug_relaxes_secret_but_never_external_ai():
    assert load_config({**OK, "DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": "dummy"})["debug"]
    with pytest.raises(ConfigError):
        load_config({**OK, "DJANGO_DEBUG": "true", "AI_EXTERNAL_HEALTH_DATA": "1"})
