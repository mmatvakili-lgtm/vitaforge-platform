"""AI-curated exercise bank (decision D-001). Source of truth for data/bank_*.json; regenerate with `python -m exercise_catalog.bank`."""


def _all():
    from . import core_mobility, lower, upper
    return {"lower": lower.ROWS, "upper": upper.ROWS, "core_mobility": core_mobility.ROWS}


ALL_BATCHES = _all()
