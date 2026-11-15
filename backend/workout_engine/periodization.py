"""Weekly periodization (mesocycle) and automatic deload.

Pure and deterministic. It can only make the prescription *easier* than the standard one (lower target RPE, fewer sets); it never raises
volume or intensity, never touches exercise selection, and the Safety Core still approves every plan (Safety > everything).
Technical defaults, NOT clinical advice (EXP-013).
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

# phase -> (RPE offset applied to the goal's standard target RPE, set multiplier)
PHASES = {
    "standard": (0.0, 1.0),
    "base": (-1.0, 1.0),       # block week 1: leave reps in reserve while the pattern settles
    "build": (-0.5, 1.0),      # week 2
    "peak": (0.0, 1.0),        # week 3: the standard target, never above it
    "deload": (-2.0, None),    # last week of the block, or triggered by sustained very high RPE
    "reentry": (-1.5, None),   # back after a long break: ease in
}
RPE_FLOOR = 5.0


def decide_phase(block_week: Optional[int], signals: Sequence[str] = (), block_weeks: int = 4) -> Tuple[str, Tuple[str, ...]]:
    """Return (phase, reasons). `signals` are descriptive analytics keys ('rpe_high', 'inactive'); unknown keys are ignored."""
    if "rpe_high" in signals:
        return "deload", ("phase:deload", "deload:auto:rpe_high")
    if "inactive" in signals:
        return "reentry", ("phase:reentry", "reentry:inactive")
    if block_week is None or block_weeks < 2:
        return "standard", ()
    w = max(1, min(int(block_week), block_weeks))
    if w == block_weeks:
        return "deload", ("phase:deload", f"deload:scheduled:{w}/{block_weeks}")
    name = ("base", "build", "peak")[min(w - 1, 2)]
    return name, (f"phase:{name}", f"block-week:{w}/{block_weeks}")


def adjust(phase: str, sets: int, rpe: float, deload_factor: float) -> Tuple[int, float]:
    """Apply a phase to the standard (sets, rpe). Never returns more sets or a higher RPE than given."""
    off, mult = PHASES[phase]
    if phase == "deload":
        new_sets = max(2, round(sets * deload_factor))
    elif phase == "reentry":
        new_sets = max(2, sets - 1)
    else:
        new_sets = sets
    return min(sets, new_sets), (max(min(RPE_FLOOR, rpe), rpe + off) if off else rpe)
