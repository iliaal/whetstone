"""Hybrid reward for a whetstone rollout.

``hard`` is deterministic and trusted to NOBODY but this evaluator: after the
agent's rollout we run the fixture's test ourselves in the post-rollout
workspace. Exit 0 -> 1 (bug fixed), else 0. The agent cannot fake it.

``soft`` is the per-skill process rubric, judged by the optimizer model on the
rollout trajectory with verbatim-evidence guarding (rubric.py).
"""
from __future__ import annotations

import subprocess
import sys

from .rubric import CompleteFn, Rubric, score_criteria, weighted_soft

DEFAULT_TEST_CMD = ["-m", "pytest", "-q"]


def run_hard(work_dir: str, test_cmd, timeout: int = 120) -> tuple[int, str]:
    """Run the fixture test in the post-rollout workspace. Returns (hard, output).

    test_cmd is the argument list AFTER the python interpreter; we always invoke
    with the trainer's own interpreter (sys.executable) so the deterministic
    check does not depend on whatever environment the agent's Bash ran in.
    """
    args = list(test_cmd) if test_cmd else list(DEFAULT_TEST_CMD)
    cmd = [sys.executable] + args
    try:
        proc = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 0, f"hard-check timeout ({timeout}s)"
    except OSError as e:
        return 0, f"hard-check error: {e}"
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return (1 if proc.returncode == 0 else 0), output[-4000:]


def _fail_reason(hard: int, criteria: dict[str, dict], test_output: str) -> str:
    parts: list[str] = []
    if not hard:
        tail = test_output.strip().splitlines()[-3:] if test_output else []
        parts.append("hard=0 (test still failing): " + " | ".join(tail))
    weak = sorted(((c["score"], n) for n, c in criteria.items()))[:2]
    weak_str = ", ".join(f"{n}={s:.2f}" for s, n in weak)
    if weak_str:
        parts.append(f"weakest criteria: {weak_str}")
    return "; ".join(parts)


def evaluate(
    work_dir: str,
    item: dict,
    trajectory_text: str,
    rubric: Rubric,
    complete: CompleteFn,
    *,
    test_timeout: int = 120,
) -> dict:
    """Return the hybrid reward + per-criterion breakdown for one rollout."""
    hard, test_output = run_hard(work_dir, item.get("test_cmd"), timeout=test_timeout)
    task = item.get("question", "")
    criteria = score_criteria(rubric, task, trajectory_text, complete)
    soft = weighted_soft(rubric, criteria)
    return {
        "hard": int(hard),
        "soft": float(soft),
        "criteria": criteria,
        "test_output": test_output,
        "fail_reason": _fail_reason(hard, criteria, test_output),
    }
