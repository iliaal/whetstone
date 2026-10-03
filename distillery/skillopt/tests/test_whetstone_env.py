"""Deterministic unit tests for the whetstone SkillOpt env (no Claude tokens).

Run from the skillopt root:  PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import argparse
import json
import os

import pytest

from skillopt.envs.whetstone.dataloader import _resolve_fixture_dir
from skillopt.envs.whetstone.evaluator import evaluate, run_detection, run_hard
from skillopt.envs.whetstone.rubric import (
    RUBRICS,
    _grounded,
    score_criteria,
    weighted_soft,
)


def _const_complete(payload: dict):
    """A stub judge that always returns the given criteria payload as JSON."""
    return lambda system, user: json.dumps(payload)


# --- code-enforced verbatim-evidence grounding ------------------------------

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


def test_essential_criterion_failure_cannot_be_offset():
    rubric = {"essential": (0.1, "required action"), "optional": (0.9, "other action")}
    criteria = {"essential": {"score": 0.2}, "optional": {"score": 1.0}}
    assert weighted_soft(rubric, criteria) == 0.92
    assert weighted_soft(
        rubric, criteria, soft_gates={"essential": {"minimum": 0.8, "cap": 0.0}},
    ) == 0.0


@pytest.mark.parametrize("score, expected", [(0.8, 0.98), (0.79999, 0.1234567)])
def test_soft_gate_respects_threshold_and_exact_cap(score, expected):
    rubric = {"essential": (0.1, "required action"), "optional": (0.9, "other action")}
    criteria = {"essential": {"score": score}, "optional": {"score": 1.0}}
    assert weighted_soft(
        rubric, criteria, soft_gates={"essential": {"minimum": 0.8, "cap": 0.1234567}},
    ) == expected


def test_multiple_failed_criteria_use_the_smallest_cap():
    rubric = {"first": (0.1, "action"), "second": (0.1, "action"), "optional": (0.8, "action")}
    criteria = {"first": {"score": 0}, "second": {"score": 0}, "optional": {"score": 1}}
    assert weighted_soft(rubric, criteria, soft_gates={
        "first": {"minimum": 1, "cap": 0.2},
        "second": {"minimum": 1, "cap": 0.4},
    }) == 0.2


def test_failed_criterion_cap_does_not_raise_a_lower_score():
    rubric = {"essential": (1.0, "required action")}
    assert weighted_soft(rubric, {"essential": {"score": 0.1}}, soft_gates={
        "essential": {"minimum": 1, "cap": 0.4},
    }) == 0.1


@pytest.mark.parametrize("score", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_judge_score_cannot_satisfy_essential_criterion(score):
    rubric = {"essential": (1.0, "required action")}
    quote = "Ran the requested test before making a source change."
    criteria = score_criteria(rubric, "q", quote, _const_complete({"criteria": {
        "essential": {"score": score, "evidence": quote},
    }}))
    assert criteria["essential"]["score"] == 0.0


@pytest.mark.parametrize("policy", [
    [], {"unknown": {"minimum": 1, "cap": 0}},
    {"essential": None}, {"essential": {"minimum": 1}},
    {"essential": {"minimum": 1, "cap": 0, "typo": 1}},
    {"essential": {"minimum": True, "cap": 0}},
    {"essential": {"minimum": "1", "cap": 0}},
    {"essential": {"minimum": -0.1, "cap": 0}},
    {"essential": {"minimum": 1.1, "cap": 0}},
    {"essential": {"minimum": 10 ** 400, "cap": 0}},
    {"essential": {"minimum": float("nan"), "cap": 0}},
    {"essential": {"minimum": 1, "cap": float("inf")}},
    {"essential": {"minimum": 1, "cap": -0.1}},
    {"essential": {"minimum": 1, "cap": 1.1}},
])
def test_invalid_soft_gate_policy_is_rejected(policy):
    with pytest.raises(ValueError, match="soft_gates"):
        weighted_soft({"essential": (1.0, "required action")}, {}, soft_gates=policy)


@pytest.mark.parametrize("hard", [0, 1])
def test_evaluation_caps_grounded_soft_without_changing_hard(tmp_path, hard):
    (tmp_path / "test_result.py").write_text(f"def test_result():\n    assert {hard} == 1\n")
    rubric = {"essential": (0.1, "required action"), "optional": (0.9, "other action")}
    quote = "Ran the requested test before making a source change."
    payload = {"criteria": {
        "essential": {"score": 0.2, "evidence": quote},
        "optional": {"score": 1.0, "evidence": quote},
    }}
    ev = evaluate(
        str(tmp_path), {"question": "q"}, quote, rubric, _const_complete(payload),
        soft_gates={"essential": {"minimum": 0.8, "cap": 0.0}},
    )
    assert ev["hard"] == hard
    assert ev["infra_error"] is False
    assert ev["criteria"]["essential"]["grounded"] is True
    assert ev["soft_uncapped"] == 0.92
    assert ev["soft"] == 0.0
    assert ev["soft_gates_failed"] == ["essential"]
    assert "soft gates failed: essential" in ev["fail_reason"]


def test_yaml_policy_reaches_adapter_rollout_scoring(tmp_path, monkeypatch):
    import yaml
    from scripts.train import get_adapter, load_config
    from skillopt.envs.whetstone import adapter as adapter_module, rollout
    from skillopt.model import backend_config

    fixture = tmp_path / "tasks" / "example"
    fixture.mkdir(parents=True)
    (fixture / "test_result.py").write_text("def test_result():\n    assert 1 == 1\n")
    for split in ("train", "val", "test"):
        split_dir = tmp_path / "splits" / split
        split_dir.mkdir(parents=True)
        (split_dir / "items.json").write_text(json.dumps([{"id": "example", "question": "q"}]))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"env": {
        "name": "whetstone", "skill_name": "ia-debugging",
        "split_dir": str(tmp_path / "splits"), "tasks_root": str(tmp_path / "tasks"),
        "out_root": str(tmp_path / "run"), "workers": 1,
        "soft_gates": {"reproduced_first": {"minimum": 1.0, "cap": 0.0}},
    }}))
    cfg = load_config(argparse.Namespace(config=str(config_path), cfg_options=[]))
    adapter = get_adapter(cfg)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.json").write_text(json.dumps(cfg))
    adapter.setup(cfg)
    batch = adapter.get_dataloader().build_eval_batch(env_num=1, split="valid_seen", seed=42)
    quote = "Ran the requested test before making a source change."
    payload = {"criteria": {
        name: {"score": 0.0 if name == "reproduced_first" else 1.0, "evidence": quote}
        for name in adapter.rubric
    }}
    monkeypatch.setattr(backend_config, "TARGET_BACKEND", "claude_code_exec")
    monkeypatch.setenv("CLAUDE_CODE_SANDBOXED", "1")
    for name in ("CLAUDE_CODE_COORDINATOR_MODE", "CLAUDE_PROJECT_DIR",
                 "CLAUDE_CODE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT"):
        monkeypatch.setenv(name, os.environ.get(name, "test"))
    monkeypatch.setattr(rollout, "run_target_exec", lambda **kwargs: (quote, quote))
    monkeypatch.setattr(adapter_module, "optimizer_complete", _const_complete(payload))
    results = adapter.rollout(adapter.build_env_from_batch(batch), "skill", str(tmp_path / "eval"))
    assert len(results) == 1
    assert results[0]["hard"] == 1
    assert results[0]["soft_uncapped"] == 0.8
    assert results[0]["soft"] == 0.0
    assert results[0]["soft_gates_failed"] == ["reproduced_first"]


@pytest.mark.parametrize("previous, current", [
    ({}, {"reproduced_first": {"minimum": 1, "cap": 0}}),
    ({"reproduced_first": {"minimum": 1, "cap": 0}}, {}),
    ({"reproduced_first": {"minimum": 1, "cap": 0}},
     {"reproduced_first": {"minimum": 1, "cap": 0.3}}),
])
def test_existing_run_cannot_resume_under_a_different_soft_policy(tmp_path, previous, current):
    from skillopt.envs.whetstone.adapter import WhetstoneAdapter

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"soft_gates": previous}))
    adapter = WhetstoneAdapter(soft_gates=current)
    with pytest.raises(ValueError, match="new out_root"):
        adapter.setup({"out_root": str(tmp_path)})
    assert json.loads(config_path.read_text()) == {"soft_gates": previous}


@pytest.mark.parametrize("weight", [0.0, 0.15])
def test_soft_gate_scores_cannot_offset_a_lost_hard_result(monkeypatch, weight):
    from skillopt.utils.scoring import compute_score

    monkeypatch.setenv("SKILLOPT_SOFT_WEIGHT", str(weight))
    baseline = [{"hard": 1, "soft": 0.0} for _ in range(5)]
    candidate = [{"hard": 1, "soft": 1.0} for _ in range(4)] + [{"hard": 0, "soft": 1.0}]
    assert compute_score(candidate)[0] < compute_score(baseline)[0]


def test_changed_soft_policy_does_not_reuse_an_uncapped_rollout(tmp_path, monkeypatch):
    import hashlib
    from skillopt.envs.whetstone import rollout
    from skillopt.model import backend_config

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "test_result.py").write_text("def test_result():\n    assert 1 == 1\n")
    out_root = tmp_path / "eval"
    out_root.mkdir()
    skill = "skill"
    (out_root / "results.jsonl").write_text(json.dumps({
        "id": "example", "skill_hash": hashlib.sha1(skill.encode()).hexdigest()[:12],
        "hard": 1, "soft": 0.92,
    }) + "\n")
    rubric = {"essential": (0.1, "required action"), "optional": (0.9, "other action")}
    quote = "Ran the requested test before making a source change."
    payload = {"criteria": {
        "essential": {"score": 0.2, "evidence": quote},
        "optional": {"score": 1.0, "evidence": quote},
    }}
    executions = []

    def target(**kwargs):
        executions.append(kwargs["work_dir"])
        return quote, quote

    monkeypatch.setattr(backend_config, "TARGET_BACKEND", "claude_code_exec")
    monkeypatch.setenv("CLAUDE_CODE_SANDBOXED", "1")
    for name in ("CLAUDE_CODE_COORDINATOR_MODE", "CLAUDE_PROJECT_DIR",
                 "CLAUDE_CODE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT"):
        monkeypatch.setenv(name, os.environ.get(name, "test"))
    monkeypatch.setattr(rollout, "run_target_exec", target)
    kwargs = {
        "items": [{"id": "example", "_fixture_dir": str(fixture)}],
        "out_root": str(out_root), "skill_content": skill, "rubric": rubric,
        "soft_gates": {"essential": {"minimum": 0.8, "cap": 0.0}},
        "complete": _const_complete(payload), "workers": 1,
    }
    results = rollout.run_batch(**kwargs)
    assert len(results) == 1
    assert results[0]["soft"] == 0.0
    assert len(executions) == 1
    assert rollout.run_batch(**kwargs) == results
    assert len(executions) == 1
    kwargs["soft_gates"]["essential"]["cap"] = 0.3
    changed = rollout.run_batch(**kwargs)
    assert len(changed) == 1
    assert changed[0]["soft"] == 0.3
    assert len(executions) == 2


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
    # The transcript is JSON-escaped stream-json, so a verbatim quote spanning
    # `\n`/`\"` matches only after normalization. The quote below spans an
    # escaped newline.
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


# --- pytest infra exits are distinct from a genuine failure -----------------

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
    # The transcript reaches the judge via agent_report. A ~280K-char report
    # overflows the judge backend and zeroes soft, so evaluate() must trim it.
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


# --- detection grading for review-style fixtures (ia-code-review) ------------

def test_run_detection_needs_localize_and_identify():
    spec = {"must_localize": ["find_user"], "must_include_any": ["inject", "concat"]}
    hit, _detail, infra = run_detection("find_user concatenates name into the SQL string -- injection", spec)
    assert hit == 1 and infra is False
    # localized but no mechanism keyword -> miss (a clean bill of health)
    assert run_detection("find_user looks clean, no issues found", spec)[0] == 0
    # mechanism keyword but not localized to the function -> miss
    assert run_detection("there might be a SQL injection somewhere in the app", spec)[0] == 0


def test_evaluate_routes_detection_without_pytest(tmp_path):
    # A detection item must be graded by run_detection, not pytest -- no test files needed.
    item = {"detection": {"must_localize": ["foo"], "must_include_any": ["leak"]}}
    ev = evaluate(str(tmp_path), item, "foo never closes the file -- a resource leak",
                  RUBRICS["ia-code-review"], lambda s, u: json.dumps({"criteria": {}}),
                  pre_test_output="", agent_diff="")
    assert ev["hard"] == 1
    assert ev["infra_error"] is False


# --- fixture path resolution is contained -----------------------------------

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
