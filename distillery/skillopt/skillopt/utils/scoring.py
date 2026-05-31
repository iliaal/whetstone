"""Scoring and hashing utilities."""
from __future__ import annotations

import hashlib
import os


def compute_score(results: list) -> tuple[float, float]:
    """Compute the selection score and soft accuracy from episode results.

    Accepts both plain dicts and :class:`~skillopt.types.RolloutResult`
    instances. Returns ``(selection, soft)`` where ``soft`` is the mean process
    score and ``selection`` is the metric the validation gate optimizes.

    LOCAL VENDOR PATCH (whetstone; see VENDORED.md): upstream returns the mean
    hard pass-rate as the first element. For a *process* skill, hard saturates
    (capable models fix tractable bugs), so the only improvable signal is soft.
    When ``SKILLOPT_SOFT_WEIGHT`` (default 0 = upstream behavior) is set, blend
    it: ``selection = mean_hard + weight * mean_soft``. Keep ``weight < 1/n_val``
    so soft can refine selection AMONG correct fixes but can never offset losing
    a fix (a single lost fix costs 1/n of hard) -- the deterministic floor holds.
    Per-item ``hard`` is untouched (still the pristine 0/1 test result).
    """
    if not results:
        return 0.0, 0.0

    def _hard(r: object) -> int:
        return int(r.hard if hasattr(r, "hard") else r.get("hard", 0))  # type: ignore[union-attr]

    def _soft(r: object) -> float:
        return float(r.soft if hasattr(r, "soft") else r.get("soft", 0.0))  # type: ignore[union-attr]

    hard = sum(_hard(r) for r in results) / len(results)
    soft = sum(_soft(r) for r in results) / len(results)
    weight = float(os.environ.get("SKILLOPT_SOFT_WEIGHT", "0") or 0)
    selection = hard + weight * soft
    return selection, soft


def skill_hash(content: str) -> str:
    """Return a short deterministic hash of skill content (for caching)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]
