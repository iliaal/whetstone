"""Hybrid reward for a whetstone rollout.

``hard`` is deterministic and trusted to NOBODY but this evaluator: after the
agent's rollout we run the fixture's PRISTINE test ourselves in a fresh grading
directory (pre-launch fixture snapshot plus the agent's non-test source edits,
see rollout.py). All tests passing per pytest's own report -> 1 (bug fixed),
else 0. Pytest "infra" exits (no tests collected, usage/collection errors) are kept
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

import ast
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from .rubric import CompleteFn, Rubric, SoftGates, score_criteria, validate_soft_gates, weighted_soft

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


# Environment variables that would let anything other than the fixture decide
# what the grading interpreter imports or how pytest is configured.
_SCRUBBED_ENV = (
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTEST_ADDOPTS", "PYTEST_PLUGINS",
)


def _interpreter() -> str:
    return sys.executable


def _grading_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _SCRUBBED_ENV}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Python 3.11+: keep the cwd (the graded workspace) off sys.path, so a
    # workspace file cannot shadow pytest or a stdlib module. Ignored before 3.11.
    env["PYTHONSAFEPATH"] = "1"
    return env


def _is_pytest_cmd(args: list[str]) -> bool:
    return len(args) >= 2 and args[0] == "-m" and args[1] == "pytest"


def _pytest_importable(env: dict[str, str], timeout: int) -> tuple[bool, str]:
    """Preflight `import pytest` from a neutral cwd, so a missing pytest is an
    infra error rather than an exit-1 'tests failed'."""
    neutral = tempfile.mkdtemp(prefix="skillopt-preflight-")
    try:
        proc = subprocess.run(
            [_interpreter(), "-c", "import pytest"], cwd=neutral, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, f"pytest preflight error: {e}"
    finally:
        shutil.rmtree(neutral, ignore_errors=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()[-1000:]
    return True, ""


_TEST_FILE_SKIP_DIRS = frozenset({"__pycache__", "build", "dist", "node_modules", "venv", "CVS", "_darcs"})


def _is_test_file(name: str) -> bool:
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _test_items(body: list[ast.stmt], prefix: list[str]) -> list[tuple[str, str]]:
    """(class path, function) pairs pytest's default collection would produce
    from one module or Test* class body. Callables bound to test_* names by
    assignment are not visible here; they show up only as extra testcases."""
    out: list[tuple[str, str]] = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out.append((".".join(prefix), node.name))
        elif isinstance(node, ast.ClassDef) and _is_unittest_case(node):
            # pytest collects unittest.TestCase subclasses by their test* methods
            # whatever the class name, and ignores the __init__ rule for them.
            out.extend((".".join(prefix + [node.name]), m.name) for m in node.body
                       if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            has_init = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "__init__"
                           for n in node.body)
            if not has_init:
                out.extend(_test_items(node.body, prefix + [node.name]))
    return out


def _is_unittest_case(node: ast.ClassDef) -> bool:
    """A class whose direct base is spelled *TestCase (unittest.TestCase,
    IsolatedAsyncioTestCase, a local TestCase import). Indirect inheritance
    through a project base class is not visible to the AST walk."""
    for base in node.bases:
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if name.endswith("TestCase"):
            return True
    return False


def expected_test_ids(work_dir: str, scope: list[str] | None = None) -> set[tuple[str, str]]:
    """JUnit (classname, name) pairs the test files under work_dir define.

    Derived by AST from the files on disk before pytest starts, so the caller
    must pass a directory whose test files are the pristine fixture copies (the
    rollout's grade dir guarantees this). `scope` restricts the walk to the
    given relative files or directories, mirroring positional pytest paths."""
    root = os.path.realpath(work_dir)
    starts = [os.path.join(root, s) for s in scope] if scope else [root]
    files: list[str] = []
    for start in starts:
        if os.path.isfile(start):
            files.append(start)
            continue
        for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames
                                 if not d.startswith(".") and d not in _TEST_FILE_SKIP_DIRS
                                 and not d.endswith(".egg"))
            files.extend(os.path.join(dirpath, n) for n in sorted(filenames) if _is_test_file(n))
    ids: set[tuple[str, str]] = set()
    for path in files:
        if os.path.islink(path):
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        module = rel[:-3].replace("/", ".")
        try:
            with open(path, "rb") as f:
                tree = ast.parse(f.read(), filename=rel)
        except (OSError, SyntaxError, ValueError):
            continue
        for cls, func in _test_items(tree.body, []):
            ids.add((f"{module}.{cls}" if cls else module, func))
    return ids


# Selection options that make pytest run a subset the AST walk cannot predict.
_SELECTION_OPTS = ("-k", "-m", "--deselect", "--ignore", "--ignore-glob", "--lf", "--last-failed",
                   "--ff", "--failed-first", "--sw", "--stepwise", "--pyargs")


# Non-selecting options whose value may follow as a separate argument.
_VALUE_OPTS = ("-p", "-c", "-o", "-W", "-r", "--tb", "--rootdir", "--confcutdir", "--basetemp",
               "--durations", "--durations-min", "--maxfail", "--junit-prefix", "--override-ini",
               "--import-mode", "--capture", "--color", "--log-level", "--log-cli-level",
               "--log-format", "--log-date-format", "--log-file", "--log-file-level",
               "--pythonwarnings", "--timeout")


def _pytest_scope(root: str, extra: list[str]) -> tuple[list[str] | None, str]:
    """Positional paths of a pytest command, or an error when the command
    selects tests in a way expected-test verification cannot model."""
    paths: list[str] = []
    skip_value = False
    for arg in extra:
        if skip_value:
            skip_value = False
            continue
        if arg.startswith("-"):
            if arg in _VALUE_OPTS:
                skip_value = True
                continue
            if any(arg == o or arg.startswith(o + "=") or (len(o) == 2 and arg.startswith(o))
                   for o in _SELECTION_OPTS):
                return None, f"test_cmd option {arg!r} selects tests; expected-test verification cannot model it"
            continue
        full = os.path.realpath(os.path.join(root, arg))
        inside = full == root or full.startswith(root + os.sep)
        if "::" in arg or not inside or not os.path.exists(full):
            return None, f"test_cmd argument {arg!r} is not a path inside the graded workspace"
        paths.append(os.path.relpath(full, root))
    return (paths or None), ""


def _junit_verdict(report_path: str, expected: set[tuple[str, str]]) -> tuple[bool, str]:
    """Require pytest's own report to show every expected test passing.

    Exit status alone is forgeable from inside the graded process (an imported
    module calling os._exit(0) skips the run), and a module-level skip exits 0
    with nothing tested. Skipped/xfailed tests are not a pass. Each expected
    (classname, name) pair, derived from the pristine test files, must appear
    as a testcase with no failure, error, or skipped child; parametrized cases
    match by "name[" prefix.

    This raises the bar for a forged report but does not close it: code under
    test runs in the pytest process, can read the report path from argv, and
    can write a report naming every expected test before calling os._exit(0).
    Closing that needs an OS sandbox that keeps the report out of reach."""
    if not expected:
        return False, "no expected tests derivable from the pristine test files"
    try:
        root = ET.parse(report_path).getroot()
    except (OSError, ET.ParseError) as e:
        return False, f"no readable pytest report ({type(e).__name__})"
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return False, "pytest report has no testsuite"
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            try:
                totals[key] += int(suite.get(key, "0"))
            except ValueError:
                return False, f"pytest report has a non-integer {key!r}"
    if totals["tests"] <= 0:
        return False, "pytest report shows no tests"
    if totals["failures"] or totals["errors"] or totals["skipped"]:
        return False, "pytest report shows non-passing tests: " + ", ".join(
            f"{k}={v}" for k, v in totals.items())
    passed: set[tuple[str, str]] = set()
    n_cases = 0
    for suite in suites:
        for case in suite.iter("testcase"):
            n_cases += 1
            if any(child.tag in ("failure", "error", "skipped") for child in case):
                return False, f"pytest report testcase {case.get('name')!r} did not pass"
            passed.add((case.get("classname", ""), case.get("name", "")))
    if n_cases != totals["tests"]:
        return False, f"pytest report lists {n_cases} testcases but claims tests={totals['tests']}"
    missing = sorted(
        f"{cls}::{func}" for cls, func in expected
        if not any(c == cls and (n == func or n.startswith(func + "[")) for c, n in passed)
    )
    if missing:
        return False, f"pytest report lacks passing results for expected tests: {', '.join(missing[:5])}"
    return True, ""


def run_hard(work_dir: str, test_cmd, timeout: int = 120) -> tuple[int, str, bool]:
    """Run the fixture test in `work_dir`. Returns (hard, output, infra_error).

    `infra_error` is True when pytest could not actually evaluate the tests
    (pytest not installed, missing test file, usage error, ...) -- distinct from
    hard=0 caused by a genuinely failing test. Always invoked with the trainer's
    own interpreter (sys.executable) so the deterministic check does not depend
    on whatever environment the agent's Bash ran in.

    For pytest commands the run is isolated from the workspace: no cache
    provider, rootdir and conftest search pinned to `work_dir`, an
    evaluator-owned empty ini (so no pytest.ini/pyproject.toml/tox.ini/setup.cfg
    in the workspace or its ancestors applies), and hard=1 additionally requires
    pytest's JUnit report to show a passing testcase for every test the
    workspace's test files define (see `_junit_verdict` for the residual).
    """
    args = list(test_cmd) if test_cmd else list(DEFAULT_TEST_CMD)
    env = _grading_env()
    if not _is_pytest_cmd(args):
        cmd = [_interpreter()] + args
        try:
            proc = subprocess.run(
                cmd, cwd=work_dir, env=env, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return 0, f"hard-check timeout ({timeout}s)", True
        except OSError as e:
            return 0, f"hard-check error: {e}", True
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        rc = proc.returncode
        infra = rc in _PYTEST_INFRA_EXITS
        if infra:
            output = f"[exit {rc}: {_PYTEST_EXIT_MEANING.get(rc, '?')}]\n" + output
        return (1 if rc == 0 else 0), output[-4000:], infra

    ok, why = _pytest_importable(env, timeout)
    if not ok:
        return 0, f"[pytest unavailable in grading interpreter {_interpreter()}]\n{why}", True

    root = os.path.realpath(work_dir)
    scope, why = _pytest_scope(root, args[2:])
    if why:
        return 0, f"[hard-check cannot verify this test_cmd: {why}]", True
    expected = expected_test_ids(root, scope)

    harness_dir = tempfile.mkdtemp(prefix="skillopt-hard-")
    try:
        ini = os.path.join(harness_dir, "pytest.ini")
        with open(ini, "w", encoding="utf-8") as f:
            f.write("[pytest]\n")
        report = os.path.join(harness_dir, f"report-{secrets.token_hex(16)}.xml")
        cmd = [_interpreter()] + args[:2] + [
            "-c", ini, f"--rootdir={root}", f"--confcutdir={root}",
            "-p", "no:cacheprovider", f"--junitxml={report}",
        ] + args[2:]
        try:
            proc = subprocess.run(
                cmd, cwd=root, env=env, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return 0, f"hard-check timeout ({timeout}s)", True
        except OSError as e:
            return 0, f"hard-check error: {e}", True
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        rc = proc.returncode
        if rc in _PYTEST_INFRA_EXITS:
            output = f"[pytest exit {rc}: {_PYTEST_EXIT_MEANING.get(rc, '?')}]\n" + output
            return 0, output[-4000:], True
        if rc != 0:
            return 0, output[-4000:], False
        passed, why = _junit_verdict(report, expected)
        if not passed:
            output = f"[hard-check rejected exit 0: {why}]\n" + output
            return 0, output[-4000:], False
        return 1, output[-4000:], False
    finally:
        shutil.rmtree(harness_dir, ignore_errors=True)


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
    soft_gates: SoftGates | None = None,
) -> dict:
    """Return the hybrid reward + per-criterion breakdown for one rollout.

    `agent_report` is the agent's final message; it is folded into a richer
    trajectory alongside the harness-verified artifacts before judging.
    """
    gates = validate_soft_gates(rubric, soft_gates)
    detection = item.get("detection")
    if detection:
        # Review-style fixture: grade the report against the hidden spec, not pytest.
        hard, test_output, infra = run_detection(agent_report, detection)
    else:
        hard, test_output, infra = run_hard(work_dir, item.get("test_cmd"), timeout=test_timeout)
    # The target transcript can reach 100K-300K chars. Past ~130K the judge
    # backend overflows, the call raises, and score_criteria zeroes soft. Keep
    # the head (early Read/repro actions, which temporal criteria ground
    # against) and the tail (final diff/report); drop the middle.
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
    soft_uncapped = weighted_soft(rubric, criteria)
    soft = weighted_soft(rubric, criteria, soft_gates=gates)
    failed = [name for name, rule in gates.items()
              if criteria[name]["score"] < rule["minimum"]]
    fail_reason = _fail_reason(hard, infra, criteria, test_output)
    if failed:
        fail_reason += "; soft gates failed: " + ", ".join(failed)
    return {
        "hard": int(hard),
        "soft": float(soft),
        "soft_uncapped": float(soft_uncapped),
        "soft_gates_failed": failed,
        "criteria": criteria,
        "test_output": test_output,
        "infra_error": bool(infra),
        "trajectory_text": trajectory_text,
        "fail_reason": fail_reason,
    }
