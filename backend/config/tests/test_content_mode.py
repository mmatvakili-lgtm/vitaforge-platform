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
