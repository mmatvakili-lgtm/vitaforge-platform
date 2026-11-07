"""Idempotent normaliser: RTL wrapper + backtick English phrases inside Persian lines."""
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent / "docs"
FA = re.compile(r"[؀-ۿ]")
PHRASE = re.compile(r"(?<![\w`-])([A-Za-z][A-Za-z0-9/.-]*(?:[ ][A-Za-z][A-Za-z0-9/.-]*){2,})(?![\w`])")
SPLIT = re.compile(r"(`[^`]*`|\[[^\]]*\]\([^)]*\)|https?://\S+|<[^>]+>)")
def fix_line(line):
    if not FA.search(line) or line.lstrip().startswith("|---"):
        return line
    parts = SPLIT.split(line)
    for i in range(0, len(parts), 2):
        parts[i] = PHRASE.sub(lambda m: f"`{m.group(1)}`", parts[i])
    return "".join(parts)
for p in sorted(ROOT.rglob("*.md")):
    t = p.read_text(encoding="utf-8")
    body = t
    if body.lstrip().startswith('<div dir="rtl">'):
        body = body.lstrip()[len('<div dir="rtl">'):].rstrip()
        body = body[:-len("</div>")] if body.endswith("</div>") else body
    out, fence = [], False
    for line in body.strip("\n").splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            out.append(line); continue
        out.append(line if fence else fix_line(line))
    p.write_text('<div dir="rtl">\n\n' + "\n".join(out) + "\n\n</div>\n", encoding="utf-8")
