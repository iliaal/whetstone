"""Hybrid reward for a whetstone rollout.

``hard`` is deterministic and trusted to NOBODY but this evaluator: after the
agent's rollout we run the fixture's PRISTINE test ourselves in the
post-rollout workspace. Exit 0 -> 1 (bug fixed), else 0. The agent cannot fake
it. Pytest "infra" exits (no tests collected, usage/collection errors) are kept
distinct from a genuine test failure, so a misconfigured workspace or an
unrestored test file does not silently look like an unfixed bug.

``soft`` is the per-skill process rubric, judged by the optimizer model on the
rollout trajectory with code-enforced verbatim-evidence grounding (rubric.py).
The trajectory is the target's tool-use transcript PLUS harness-verified
artifacts -- the real pre/post test runs and a harness-computed diff of the
agent's source changes. The transcript is the full ordered stream (Read/Bash/
Edit events) only when the rollout runs nested in a Claude Code session
(``CLAUDE_CODE_COORDINATOR_MODE=1``); standalone, ``--output-format text``
returns just the final message. The harness artifacts are therefore the
always-present ground truth: outcome criteria ("red->green", what changed)
ground against them either way; temporal criteria ("reproduced FIRST") are fully
grounded only when the transcript stream is present.
"""
from __future__ import annotations

import subprocess
import sys

from .rubric import CompleteFn, Rubric, score_criteria, weighted_soft

DEFAULT_TEST_CMD = ["-m", "pytest", "-q"]

# pytest exit codes that mean "the check could not run", not "the fix failed":
#   2 collection error/interrupted, 3 internal error, 4 usage error,
#   5 no tests collected. Treat these as infra, never as hard=0-the-bug-stands.
_PYTEST_INFRA_EXITS = {2, 3, 4, 5}
_PYTEST_EXIT_MEANING = {
    2: "collection error or interrupted",
    3: "internal pytest error",
    4: "usage error (bad pytest invocation)",
    5: "no tests collected -- test file missing or not restored",
}


def run_hard(work_dir: str, test_cmd, timeout: int = 120) -> tuple[int, str, bool]:
    """Run the fixture test in `work_dir`. Returns (hard, output, infra_error).

    `infra_error` is True when pytest could not actually evaluate the tests
    (missing test file, usage error, ...) -- distinct from hard=0 caused by a
    genuinely failing test. Always invoked with the trainer's own interpreter
    (sys.executable) so the deterministic check does not depend on whatever
    environment the agent's Bash ran in.
    """
    args = list(test_cmd) if test_cmd else list(DEFAULT_TEST_CMD)
    cmd = [sys.executable] + args
    try:
        proc = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 0, f"hard-check timeout ({timeout}s)", True
    except OSError as e:
        return 0, f"hard-check error: {e}", True
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    rc = proc.returncode
    infra = rc in _PYTEST_INFRA_EXITS
    if infra:
        output = f"[pytest exit {rc}: {_PYTEST_EXIT_MEANING.get(rc, '?')}]\n" + output
    return (1 if rc == 0 else 0), output[-4000:], infra


def run_detection(agent_report: str, spec: dict) -> tuple[int, str, bool]:
    """Hard signal for review-style fixtures: did the agent's report NAME the
    planted defect?

    Used for skills that REPORT rather than edit (ia-code-review), where pytest
    red->green does not apply. `spec` lives in ``splits/items.json`` -- which is
    NEVER copied into the agent's workspace -- so the agent cannot read it as an
    answer key. Fields:
      ``must_localize``    -- report must reference at least one (the buggy
                              function/file/symbol)
      ``must_include_any`` -- report must contain at least one (a keyword
                              identifying the defect's mechanism)
    Match is normalized substring (lowercased, stream-json escapes flattened).
    Returns ``(hard, detail, infra=False)`` to mirror ``run_hard``."""
    t = " ".join((agent_report or "").replace("\\n", " ").replace("\\t", " ").split()).lower()
    loc = [s for s in spec.get("must_localize", []) if s.lower() in t]
    kw = [s for s in spec.get("must_include_any", []) if s.lower() in t]
    localized = bool(loc) if spec.get("must_localize") else True
    identified = bool(kw) if spec.get("must_include_any") else True
    hard = 1 if (localized and identified) else 0
    detail = (f"[detection] localized={localized} (hits={loc[:3]}) "
              f"identified={identified} (hits={kw[:3]})")
    return hard, detail, False


def _verified_block(pre_output: str, post_output: str, agent_diff: str, hard: int) -> str:
    """Harness-produced evidence prepended to the judge's trajectory. None of it
    comes from the agent, so a rubric criterion grounded against it cannot be
    satisfied by the agent merely claiming it did the work."""
    return "\n".join([
        "[HARNESS-VERIFIED ARTIFACTS -- produced by the evaluator, not the agent]",
        "Pre-fix test run (baseline, before the agent edited anything):",
        (pre_output or "(not captured)").strip()[-1500:],
        "",
        f"Post-fix test run (pristine test restored) -> hard={hard}:",
        (post_output or "(not captured)").strip()[-1500:],
        "",
        "Agent's source changes (unified diff, harness-computed):",
        (agent_diff or "(no source changes detected)").strip()[-3000:],
    ])


def _fail_reason(hard: int, infra: bool, criteria: dict[str, dict], test_output: str) -> str:
    parts: list[str] = []
    if infra:
        head = test_output.strip().splitlines()[:1]
        parts.append("hard-check could not run: " + (head[0] if head else "infra error"))
    elif not hard:
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
    agent_report: str,
    rubric: Rubric,
    complete: CompleteFn,
    *,
    test_timeout: int = 120,
    pre_test_output: str = "",
    agent_diff: str = "",
) -> dict:
    """Return the hybrid reward + per-criterion breakdown for one rollout.

    `agent_report` is the agent's final message; it is folded into a richer
    trajectory alongside the harness-verified artifacts before judging.
    """
    detection = item.get("detection")
    if detection:
        # Review-style fixture: grade the report against the hidden spec, not pytest.
        hard, test_output, infra = run_detection(agent_report, detection)
    else:
        hard, test_output, infra = run_hard(work_dir, item.get("test_cmd"), timeout=test_timeout)
    # The target transcript can be 100K-300K chars (the --output-format text
    # capture is the full stream, not just the final message). Fed whole to the
    # judge it overflows the judge backend and the call raises -> the except path
    # in score_criteria silently zeroes soft (observed: every rollout whose report
    # exceeded ~130K chars judged soft=0/grounded=None, while a 121K one scored a
    # clean 0.85). Keep the head (early Read/repro actions, which the temporal
    # criteria ground against) and the tail (final diff/report), drop the middle.
    report = agent_report or "(no final report)"
    _HEAD, _TAIL = 30000, 30000
    if len(report) > _HEAD + _TAIL:
        report = report[:_HEAD] + "\n\n[... trajectory trimmed for judge budget ...]\n\n" + report[-_TAIL:]
    trajectory_text = (
        _verified_block(pre_test_output, test_output, agent_diff, hard)
        + "\n\n[AGENT FINAL REPORT]\n"
        + report
    )
    task = item.get("question", "")
    criteria = score_criteria(rubric, task, trajectory_text, complete)
    soft = weighted_soft(rubric, criteria)
    return {
        "hard": int(hard),
        "soft": float(soft),
        "criteria": criteria,
        "test_output": test_output,
        "infra_error": bool(infra),
        "trajectory_text": trajectory_text,
        "fail_reason": _fail_reason(hard, infra, criteria, test_output),
    }
