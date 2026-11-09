import json
import pathlib

from config.routing import goes_to_api


def _ops():
    return json.loads((pathlib.Path(__file__).resolve().parents[3] / "tools" / "api_index.json").read_text(encoding="utf-8"))


def test_every_spec_operation_path_is_served_by_the_api_app():
    """Regression: /api/v1/health/* was wrongly sent to Django, so /health/screening returned 404."""
    for _id, _m, path, _tag in _ops():
        concrete = path.replace("{", "").replace("}", "") if "{" not in path else path.split("{")[0] + "x"
        assert goes_to_api("/api/v1" + concrete, False), (_id, path)


def test_root_page_only_in_dev_content_mode():
    assert goes_to_api("/", True) and not goes_to_api("/", False)
