"""Docs linter: enforces docs/LANGUAGE_POLICY.md. Exit 1 on violations."""
import re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent / "docs"
FA = re.compile(r"[؀-ۿ]")
CODE = re.compile(r"`[^`]*`")
SKIP_SUFFIX = {".yaml"}
errs = []
for p in sorted(ROOT.rglob("*.md")):
    t = p.read_text(encoding="utf-8")
    if not t.lstrip().startswith('<div dir="rtl">'):
        errs.append(f"{p.relative_to(ROOT)}: missing rtl wrapper")
    infence = False
    for i, line in enumerate(t.splitlines(), 1):
        if line.strip().startswith("```"):
            infence = not infence
            continue
        if infence or line.lstrip().startswith(("|---", "#")) and not FA.search(line):
            continue
        plain = CODE.sub("", line)
        plain = re.sub(r"\[[^\]]*\]\([^)]*\)|https?://\S+|<[^>]+>", "", plain)
        if FA.search(plain) and re.search(r"(?<![\w-])[A-Za-z]{3,}(?:[ ][A-Za-z]{3,}){2,}", plain):
            errs.append(f"{p.relative_to(ROOT)}:{i}: English phrase inside Persian line: {line.strip()[:70]}")
for e in errs[:80]:
    print(e)
print(f"violations: {len(errs)}")
sys.exit(1 if errs else 0)
