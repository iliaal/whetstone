"""Deterministic unit tests for the whetstone SkillOpt env (no Claude tokens).

Run from the skillopt root:  PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import json

import pytest

from skillopt.envs.whetstone.dataloader import _resolve_fixture_dir
from skillopt.envs.whetstone.evaluator import evaluate, run_hard
from skillopt.envs.whetstone.rubric import (
    RUBRICS,
    _grounded,
    score_criteria,
    weighted_soft,
)


def _const_complete(payload: dict):
    """A stub judge that always returns the given criteria payload as JSON."""
    return lambda system, user: json.dumps(payload)


# --- CR-001: code-enforced verbatim-evidence grounding -----------------------

def test_ungrounded_evidence_scores_zero():
    rubric = {"reproduced_first": (1.0, "a reproduction step is executed")}
    payload = {"criteria": {"reproduced_first": {
        "score": 1.0, "evidence": "THIS QUOTE IS NOWHERE IN THE TRAJECTORY"}}}
    out = score_criteria(rubric, "task", "ran pytest, the test was red", _const_complete(payload))
    assert out["reproduced_first"]["score"] == 0.0
    assert out["reproduced_first"]["grounded"] is False


def test_grounded_evidence_is_kept():
    rubric = {"reproduced_first": (1.0, "a reproduction step is executed")}
    trajectory = "I ran python -m pytest and the test was RED before any edit"
    payload = {"criteria": {"reproduced_first": {
        "score": 1.0, "evidence": "ran python -m pytest and the test was RED"}}}
    out = score_criteria(rubric, "task", trajectory, _const_complete(payload))
    assert out["reproduced_first"]["score"] == 1.0
    assert out["reproduced_first"]["grounded"] is True
    assert weighted_soft(rubric, out) == 1.0


def test_empty_evidence_scores_zero():
    rubric = {"reproduced_first": (1.0, "a reproduction step is executed")}
    payload = {"criteria": {"reproduced_first": {"score": 1.0, "evidence": ""}}}
    out = score_criteria(rubric, "task", "some trajectory text", _const_complete(payload))
    assert out["reproduced_first"]["score"] == 0.0


def test_shipped_rubric_weights_sum_to_one():
    for name, rubric in RUBRICS.items():
        total = round(sum(w for w, _ in rubric.values()), 6)
        assert total == 1.0, f"{name} weights sum to {total}, expected 1.0"


def test_json_escaped_trajectory_grounds():
    # The pilot's root cause: the transcript is JSON-escaped stream-json, so a
    # verbatim quote spanning a `\n`/`\"` failed to match until normalization
    # un-escapes it. The quote below spans an escaped newline.
    traj = r'{"text": "1 passed, 1 failed\nAssertionError: assert [1, 2] == [2, 4]\n"}'
    ev = "1 passed, 1 failed AssertionError: assert [1, 2] == [2, 4]"
    assert _grounded(ev, traj) is True


def test_stitched_quote_grounds():
    # A cooperative judge stitches two real spans with an ellipsis; one of them
    # is a long contiguous run, so it grounds.
    traj = ("step1: ran python -m pytest -q and saw AssertionError in "
            "test_doubles_all; step2: edited asyncwork.py line 15")
    ev = "ran python -m pytest -q and saw AssertionError ... edited asyncwork.py line 15"
    assert _grounded(ev, traj) is True


def test_fabricated_evidence_rejected():
    # Domain-plausible but fabricated: shares no long contiguous run.
    traj = ("ran python -m pytest; 1 passed 1 failed; AssertionError in "
            "test_doubles_all; edited asyncwork.py line 15")
    fake = "the agent contemplated seventeen alternative architectures before refactoring"
    assert _grounded(fake, traj) is False


# --- CR-006: pytest infra exits are distinct from a genuine failure ----------

def test_run_hard_no_tests_collected_is_infra(tmp_path):
    # Empty workspace -> pytest exit 5 (no tests collected) -> infra, not a fix failure.
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert hard == 0
    assert infra is True


def test_run_hard_passing_test(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    hard, _output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert hard == 1
    assert infra is False


def test_run_hard_failing_test_is_not_infra(tmp_path):
    (tmp_path / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    hard, _output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert hard == 0
    assert infra is False  # genuine failure, NOT infra


# --- trajectory bounding: an oversized transcript must not crash the judge -----

def test_oversized_agent_report_is_bounded_before_judge(tmp_path):
    # Regression: the target transcript reaches the judge via agent_report. A
    # ~280K-char report fed whole overflowed the judge backend and the call
    # raised, silently zeroing soft (grounded=None) for every large rollout while
    # a 121K one scored fine. evaluate() must trim it to a judge-safe size.
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    seen = {}

    def capture_complete(system, user):
        seen["user"] = user
        return json.dumps({"criteria": {}})

    item = {"question": "q", "test_cmd": ["-m", "pytest", "-q"]}
    evaluate(
        str(tmp_path), item, "X" * 280000,
        RUBRICS["ia-debugging"], capture_complete,
        pre_test_output="", agent_diff="",
    )
    # the trajectory handed to the judge must sit well under the ~130K overflow point
    assert len(seen["user"]) < 100000
    assert "trajectory trimmed" in seen["user"]


# --- CR-004 / CR-010: fixture path resolution is contained -------------------

def test_fixture_resolves_legit(tmp_path):
    (tmp_path / "tasks" / "dbg-001").mkdir(parents=True)
    resolved = _resolve_fixture_dir(str(tmp_path / "tasks"), {"id": "dbg-001"})
    assert resolved.endswith("dbg-001")


def test_fixture_relative_traversal_rejected(tmp_path):
    (tmp_path / "tasks").mkdir()
    with pytest.raises(ValueError):
        _resolve_fixture_dir(str(tmp_path / "tasks"), {"id": "x", "fixture": "../../etc"})


def test_fixture_absolute_escape_rejected(tmp_path):
    (tmp_path / "tasks").mkdir()
    with pytest.raises(ValueError):
        _resolve_fixture_dir(str(tmp_path / "tasks"), {"id": "x", "fixture": "/etc"})


def test_fixture_missing_id_and_fixture_rejected(tmp_path):
    (tmp_path / "tasks").mkdir()
    with pytest.raises(ValueError):
        _resolve_fixture_dir(str(tmp_path / "tasks"), {"id": "", "fixture": ""})
