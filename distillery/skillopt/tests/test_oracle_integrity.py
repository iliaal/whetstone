"""Hard-check oracle integrity for the whetstone rollout (no Claude tokens).

The target agent is a stub that performs the edits a reward-hacking model
could make; grading must not award hard=1 for any of them.

Run from the skillopt root:  PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from skillopt.envs.whetstone import evaluator, rollout
from skillopt.envs.whetstone.evaluator import run_hard

BUGGY = "def answer():\n    return 0\n"
FIXED = "def answer():\n    return 42\n"
TEST = "from bug import answer\n\n\ndef test_answer():\n    assert answer() == 42\n"
RUBRIC = {"essential": (1.0, "required action")}


@pytest.fixture
def fixture_dir(tmp_path):
    d = tmp_path / "tasks" / "case"
    d.mkdir(parents=True)
    (d / "bug.py").write_text(BUGGY)
    (d / "test_bug.py").write_text(TEST)
    return d


@pytest.fixture(autouse=True)
def _isolate_process_state(monkeypatch):
    # process_one edits these env vars; restore them after each test.
    monkeypatch.setenv("CLAUDE_CODE_SANDBOXED", "1")
    for name in ("CLAUDE_CODE_COORDINATOR_MODE", "CLAUDE_PROJECT_DIR",
                 "CLAUDE_CODE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT"):
        monkeypatch.setenv(name, os.environ.get(name, "test"))
    monkeypatch.setattr(rollout, "_PINNED_FIXTURES", {})


def _run(monkeypatch, tmp_path, fixture_dir, agent):
    def target(**kwargs):
        agent(Path(kwargs["work_dir"]))
        return "done", "stub"

    monkeypatch.setattr(rollout, "run_target_exec", target)
    return rollout.process_one(
        {"id": "case", "_fixture_dir": str(fixture_dir), "question": "Fix answer",
         "test_cmd": ["-m", "pytest", "-q"]},
        str(tmp_path / "out"), "skill", RUBRIC,
        complete=lambda _s, _u: json.dumps({"criteria": {}}),
    )


def test_genuine_fix_scores_hard(monkeypatch, tmp_path, fixture_dir):
    r = _run(monkeypatch, tmp_path, fixture_dir, lambda w: (w / "bug.py").write_text(FIXED))
    assert (r["hard"], r["infra_error"], r["integrity_error"]) == (1, False, False)


def test_no_change_scores_zero(monkeypatch, tmp_path, fixture_dir):
    r = _run(monkeypatch, tmp_path, fixture_dir, lambda w: None)
    assert (r["hard"], r["infra_error"], r["integrity_error"]) == (0, False, False)


def test_mutating_the_host_fixture_is_an_integrity_failure(monkeypatch, tmp_path, fixture_dir):
    def agent(_work):
        (fixture_dir / "test_bug.py").write_text("def test_answer():\n    pass\n")

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    assert r["hard"] == 0
    assert r["integrity_error"] is True
    assert "original fixture" in r["fail_reason"]


def test_adding_a_conftest_to_the_host_fixture_is_an_integrity_failure(
        monkeypatch, tmp_path, fixture_dir):
    r = _run(monkeypatch, tmp_path, fixture_dir,
             lambda _w: (fixture_dir / "conftest.py").write_text("import os\nos._exit(0)\n"))
    assert r["hard"] == 0
    assert r["integrity_error"] is True


def test_fixture_changed_between_rollouts_is_refused(monkeypatch, tmp_path, fixture_dir):
    first = _run(monkeypatch, tmp_path, fixture_dir, lambda w: None)
    assert first["integrity_error"] is False
    (fixture_dir / "test_bug.py").write_text("def test_answer():\n    pass\n")
    second = _run(monkeypatch, tmp_path, fixture_dir, lambda w: None)
    assert second["hard"] == 0
    assert second["integrity_error"] is True


EXIT0 = "import os\nos._exit(0)\n"


@pytest.mark.parametrize("name, content", [
    ("conftest.py", EXIT0),
    ("pytest.py", EXIT0),
    ("sitecustomize.py", EXIT0),
    ("usercustomize.py", EXIT0),
    ("evil.pth", "import os; os._exit(0)\n"),
    ("pytest.ini", "[pytest]\naddopts = -p no:python\n"),
    ("pyproject.toml", "[tool.pytest.ini_options]\naddopts = '-k nothing_matches'\n"),
    ("setup.cfg", "[tool:pytest]\npython_files = nothing_*.py\n"),
    ("tox.ini", "[pytest]\npython_functions = nothing_*\n"),
    ("test_bug.py", "def test_answer():\n    pass\n"),
    ("test_extra.py", "def test_extra():\n    pass\n"),
    ("sub/conftest.py", EXIT0),
])
def test_workspace_injection_does_not_pass(monkeypatch, tmp_path, fixture_dir, name, content):
    def agent(work):
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    assert r["hard"] == 0, r["fail_reason"]
    assert r["integrity_error"] is False


@pytest.mark.parametrize("source", [
    "import os\nos._exit(0)\n",
    "import pytest\npytest.skip('nope', allow_module_level=True)\n",
])
def test_source_edit_that_forges_exit_zero_does_not_pass(
        monkeypatch, tmp_path, fixture_dir, source):
    r = _run(monkeypatch, tmp_path, fixture_dir, lambda w: (w / "bug.py").write_text(source))
    assert r["hard"] == 0, r["fail_reason"]


def test_source_replaced_by_symlink_is_not_followed(monkeypatch, tmp_path, fixture_dir):
    outside = tmp_path / "outside_fixed.py"
    outside.write_text(FIXED)

    def agent(work):
        (work / "bug.py").unlink()
        (work / "bug.py").symlink_to(outside)

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    assert r["hard"] == 0


def test_missing_pytest_is_infra_error(monkeypatch, tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    python = venv / "bin" / "python"
    probe = subprocess.run([str(python), "-c", "import pytest"], capture_output=True)
    assert probe.returncode != 0, "venv unexpectedly provides pytest"
    work = tmp_path / "work"
    work.mkdir()
    (work / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    monkeypatch.setattr(evaluator, "_interpreter", lambda: str(python))
    hard, output, infra = run_hard(str(work), ["-m", "pytest", "-q"], timeout=60)
    assert (hard, infra) == (0, True)
    assert "pytest unavailable" in output


def test_ancestor_pytest_config_is_ignored(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -k nothing_matches\n")
    (tmp_path / "conftest.py").write_text(EXIT0)
    work = tmp_path / "work"
    work.mkdir()
    (work / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    hard, _output, infra = run_hard(str(work), ["-m", "pytest", "-q"], timeout=60)
    assert (hard, infra) == (0, False)


HELPER_FIX = "from helper import FORTY_TWO\n\n\ndef answer():\n    return FORTY_TWO\n"


def test_fix_that_imports_a_new_helper_module_scores_hard(monkeypatch, tmp_path, fixture_dir):
    def agent(work):
        (work / "helper.py").write_text("FORTY_TWO = 42\n")
        (work / "bug.py").write_text(HELPER_FIX)

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    assert (r["hard"], r["infra_error"], r["integrity_error"]) == (1, False, False), r["fail_reason"]


def test_fix_that_imports_a_new_subpackage_scores_hard(monkeypatch, tmp_path, fixture_dir):
    def agent(work):
        (work / "lib").mkdir()
        (work / "lib" / "__init__.py").write_text("")
        (work / "lib" / "consts.py").write_text("FORTY_TWO = 42\n")
        (work / "bug.py").write_text("from lib.consts import FORTY_TWO\n\n\ndef answer():\n    return FORTY_TWO\n")

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    assert r["hard"] == 1, r["fail_reason"]


BREAKS_RUN = "raise SystemExit(3)\n"


@pytest.mark.parametrize("name", [
    "conftest.py", "sub/conftest.py", "pytest.py", "py.py", "_pytest_shim.py", "pluggy_x.py",
    "sitecustomize.py", "usercustomize.py", "json.py", "test_extra.py", "extra_test.py",
    ".hidden/mod.py", "__init__.py",
])
def test_new_implicitly_loaded_files_are_not_graded(monkeypatch, tmp_path, fixture_dir, name):
    def agent(work):
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BREAKS_RUN)
        (work / "bug.py").write_text(FIXED)

    r = _run(monkeypatch, tmp_path, fixture_dir, agent)
    # The genuine fix passes only if the planted file never reached the grade dir.
    assert r["hard"] == 1, r["fail_reason"]


def test_graded_files_admits_only_eligible_new_sources(tmp_path):
    snapshot = {"bug.py": BUGGY.encode(), "test_bug.py": TEST.encode()}
    work = tmp_path / "work"
    work.mkdir()
    for name in ("helper.py", "conftest.py", "pytest.py", "sitecustomize.py", "evil.pth",
                 "pytest.ini", "data.json", "test_new.py", "os.py", "__init__.py"):
        (work / name).write_text("x = 1\n")
    (work / "bug.py").write_text(FIXED)
    (work / "test_bug.py").write_text(TEST)
    (tmp_path / "outside.py").write_text("x = 1\n")
    (work / "linked.py").symlink_to(tmp_path / "outside.py")
    assert sorted(rollout._graded_files(snapshot, str(work))) == ["bug.py", "helper.py", "test_bug.py"]


@pytest.mark.parametrize("rel", [
    "py.py", "_pytest_shim.py", "pluggy_x.py", "usercustomize.py", ".hidden/mod.py",
    "pkg/.hidden.py", "json.py", "pytest_plugin.py", "packaging.py",
])
def test_new_file_filter_rejects_shadowing_and_hidden_names(rel):
    assert not rollout._new_file_eligible(rel, set())


def test_new_files_over_the_count_limit_are_all_dropped(monkeypatch, tmp_path):
    monkeypatch.setattr(rollout, "_NEW_FILE_MAX_COUNT", 2)
    work = tmp_path / "work"
    work.mkdir()
    for i in range(3):
        (work / f"mod{i}.py").write_text("x = 1\n")
    assert rollout._new_agent_files({}, str(work)) == {}


def _forge_source(report_xml: str) -> str:
    return (
        "import os, sys\n"
        "path = next(a.split('=', 1)[1] for a in sys.argv if a.startswith('--junitxml='))\n"
        f"open(path, 'w').write({report_xml!r})\n"
        "os._exit(0)\n"
    )


def test_forged_minimal_junit_report_is_rejected(monkeypatch, tmp_path, fixture_dir):
    forged = '<testsuite tests="1" failures="0" errors="0" skipped="0"/>'
    r = _run(monkeypatch, tmp_path, fixture_dir, lambda w: (w / "bug.py").write_text(_forge_source(forged)))
    assert r["hard"] == 0, r["fail_reason"]


def test_forged_report_without_the_expected_testcase_is_rejected(monkeypatch, tmp_path, fixture_dir):
    forged = ('<testsuite tests="1" failures="0" errors="0" skipped="0">'
              '<testcase classname="test_bug" name="test_something_else"/></testsuite>')
    r = _run(monkeypatch, tmp_path, fixture_dir, lambda w: (w / "bug.py").write_text(_forge_source(forged)))
    assert r["hard"] == 0, r["fail_reason"]


@pytest.mark.parametrize("xml, ok", [
    ('<testsuite tests="1"/>', False),
    ('<testsuite tests="1"><testcase classname="test_bug" name="test_other"/></testsuite>', False),
    ('<testsuite tests="1"><testcase classname="other" name="test_answer"/></testsuite>', False),
    ('<testsuite tests="2"><testcase classname="test_bug" name="test_answer"/></testsuite>', False),
    ('<testsuite tests="1"><testcase classname="test_bug" name="test_answer"><skipped/></testcase>'
     '</testsuite>', False),
    ('<testsuite tests="1"><testcase classname="test_bug" name="test_answer"/></testsuite>', True),
])
def test_junit_verdict_requires_each_expected_test(tmp_path, xml, ok):
    report = tmp_path / "r.xml"
    report.write_text(xml)
    passed, why = evaluator._junit_verdict(str(report), {("test_bug", "test_answer")})
    assert passed is ok, why


def test_classes_and_parametrized_tests_are_recognised(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "test_shapes.py").write_text(
        "import pytest\n\n\n"
        "@pytest.mark.parametrize('n', [1, 2])\n"
        "def test_param(n):\n    assert n > 0\n\n\n"
        "class TestGroup:\n    def test_method(self):\n        assert True\n\n"
        "    class TestInner:\n        def test_inner(self):\n            assert True\n"
    )
    assert evaluator.expected_test_ids(str(tmp_path)) == {
        ("pkg.test_shapes", "test_param"),
        ("pkg.test_shapes.TestGroup", "test_method"),
        ("pkg.test_shapes.TestGroup.TestInner", "test_inner"),
    }
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert (hard, infra) == (1, False), output


def test_unmodelled_test_selection_is_infra(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q", "-k", "ok"], timeout=60)
    assert (hard, infra) == (0, True)
    assert "selects tests" in output


def test_positional_test_path_scopes_expected_tests(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    (tmp_path / "test_other.py").write_text("def test_other():\n    assert 1 == 2\n")
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q", "test_ok.py"], timeout=60)
    assert (hard, infra) == (1, False), output


@pytest.mark.parametrize("opts", [["-p", "no:cacheprovider"], ["--tb", "short"], ["-r", "a"]])
def test_value_taking_options_are_not_paths(tmp_path, opts):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q", *opts], timeout=60)
    assert (hard, infra) == (1, False), output


def test_unittest_case_without_test_prefix_is_expected(tmp_path):
    (tmp_path / "test_answer.py").write_text(
        "import unittest\n\n\n"
        "class AnswerChecks(unittest.TestCase):\n"
        "    def test_answer(self):\n        self.assertEqual(42, 42)\n"
    )
    assert evaluator.expected_test_ids(str(tmp_path)) == {("test_answer.AnswerChecks", "test_answer")}
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert (hard, infra) == (1, False), output


def test_failing_unittest_case_scores_zero(tmp_path):
    (tmp_path / "test_answer.py").write_text(
        "from unittest import TestCase\n\n\n"
        "class AnswerChecks(TestCase):\n"
        "    def test_answer(self):\n        self.assertEqual(41, 42)\n"
    )
    hard, output, infra = run_hard(str(tmp_path), ["-m", "pytest", "-q"], timeout=60)
    assert (hard, infra) == (0, False), output
