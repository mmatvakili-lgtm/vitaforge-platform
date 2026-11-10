"""The frontend client/types are generated from the OpenAPI spec; stale output or drifted constants must fail CI."""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _gen():
    spec = importlib.util.spec_from_file_location("gen_frontend_api", ROOT / "tools/gen_frontend_api.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "backend"))
    spec.loader.exec_module(m)
    return m


def test_generated_frontend_files_are_current():
    m = _gen()
    ts, msg = m.build()
    assert (ROOT / "frontend/src/lib/api/generated.ts").read_text(encoding="utf-8") == ts, "run: python3 tools/gen_frontend_api.py"
    assert (ROOT / "frontend/src/messages/safety.generated.json").read_text(encoding="utf-8") == msg, "run: python3 tools/gen_frontend_api.py"


def _tuple(src: str, name: str):
    m = re.search(rf"export const {name} = \[(.*?)\] as const", src, re.S)
    return tuple(re.findall(r'"([^"]+)"', m.group(1)))


def test_frontend_onboarding_constants_match_backend():
    from devserver.app import SCREENING, SCREENING_VERSION
    from exercise_catalog.schema import EQUIPMENT
    from workout_engine.models import GOALS, LEVELS
    src = (ROOT / "frontend/src/lib/onboarding.ts").read_text(encoding="utf-8")
    assert _tuple(src, "SCREENING_QUESTIONS") == tuple(SCREENING)
    assert _tuple(src, "GOALS") == tuple(GOALS)
    assert _tuple(src, "LEVELS") == tuple(LEVELS)
    assert _tuple(src, "EQUIPMENT") == tuple(EQUIPMENT)
    assert f"SCREENING_VERSION = {SCREENING_VERSION};" in src
