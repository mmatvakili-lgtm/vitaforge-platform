import json
import pathlib

from . import ALL_BATCHES

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
for name, rows in ALL_BATCHES.items():
    (DATA / f"bank_{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(name, len(rows))
