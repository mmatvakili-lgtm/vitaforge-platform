"""Outbox worker: drains due messages. Each phase is its own transaction so no database lock is held while talking to an SMTP server:
   tx1 claim (row lock, status -> processing + lease)  |  network send (no store access)  |  tx2 record the result."""
from __future__ import annotations

import contextlib
from collections import Counter
from typing import Dict


def process_due(store, outbox, limit: int = 50) -> Dict[str, int]:
    tx = getattr(store, "transaction", None) or contextlib.nullcontext
    with tx():
        ids = outbox.due_ids()[:limit]
    out: Counter = Counter()
    for mid in ids:
        with tx():
            claimed = outbox.claim(mid)
        if not claimed:
            with tx():
                st = outbox.status_of(mid)
            out[st if st in ("expired", "failed") else "skipped"] += 1      # stale/expired/failed at claim time are reported as such
            continue
        result, error = outbox.attempt(claimed)
        with tx():
            out[outbox.finish(mid, result, error)] += 1
    return dict(out)
