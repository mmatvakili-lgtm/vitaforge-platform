"""ADR-0001/0002: safety_core is pure; it must not import frameworks, LLM or sibling modules."""
import ast, pathlib

FORBIDDEN = {"django", "rest_framework", "celery", "requests", "httpx", "openai", "anthropic", "ai_gateway", "workout_engine", "entitlements"}


def test_safety_core_imports_only_stdlib_and_itself():
    root = pathlib.Path(__file__).resolve().parent.parent
    for f in root.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            for n in names:
                assert n.split(".")[0] not in FORBIDDEN, f"{f.name} imports {n}"


def test_entitlements_and_gateway_do_not_import_django():
    base = pathlib.Path(__file__).resolve().parents[3]
    for pkg in ("ai_gateway", "entitlements", "workout_engine"):
        for f in (base / pkg).glob("*.py"):
            src = f.read_text(encoding="utf-8")
            assert "django" not in src and "rest_framework" not in src, f"{pkg}/{f.name}"
