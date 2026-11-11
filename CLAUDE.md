# VitaForge — agent notes
- Read docs/PROJECT_STATE.md (truth), docs/EXECUTION_ROADMAP.md (next), docs/RELEASE_CHECKLIST.md.
- Order: Safety > privacy/security > scientific accuracy > product > UX. Safety Core is deterministic and the sole approver of exercises/plans.
- Never fabricate approvals, sources, licenses, prices, nutrient values or test results. Never delete/weaken tests. No external AI with health data.
- Code/comments English; docs Persian with `<div dir="rtl">`; after doc edits run `python3 tools/normalize_docs.py && python3 tools/lint_docs.py`.
- Tests: `cd backend && python -m pytest -q <focused>`; frontend: `node --experimental-strip-types --test`.
- Commits end with the Co-Authored-By / Claude-Session lines.
