"""Deterministic unit tests for the whetstone SkillOpt env (no Claude tokens).

Run from the skillopt root:  PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import json

import pytest

from skillopt.envs.whetstone.dataloader import _resolve_fixture_dir
from skillopt.envs.whetstone.evaluator import run_hard
from skillopt.envs.whetstone.rubric import RUBRICS, score_criteria, weighted_soft


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
