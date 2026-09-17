import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "whetstone"
HOOK = PLUGIN / "hooks" / "inject-skills.sh"
SPEC = importlib.util.spec_from_file_location("jev_skills", PLUGIN / "hooks" / "jev-skills.py")
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def run_hook(prompt, env):
    payload = {
        "tool_input": {
            "prompt": prompt,
            "subagent_type": "general-purpose",
            "model": "sonnet",
            "run_in_background": True,
        }
    }
    result = subprocess.run(
        ["bash", str(HOOK)], input=json.dumps(payload), text=True,
        capture_output=True, env=env, timeout=5, check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def fake_jev(tmp_path, answers):
    executable = tmp_path / "jev"
    log = tmp_path / "request.json"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "request = json.load(sys.stdin)\n"
        f"Path({str(log)!r}).write_text(json.dumps(request))\n"
        "answers = {key: {'type': 'noul', 'noul': 0.01} for key in request['questions']}\n"
        f"answers.update({answers!r})\n"
        "print(json.dumps({'schema_version': 1, 'status': 'ok', 'model': 'jev-1.13.0', 'answers': answers}))\n"
    )
    executable.chmod(0o700)
    env = {key: value for key, value in os.environ.items() if not key.startswith("WHETSTONE_JEV")}
    env["WHETSTONE_JEV_COMMAND"] = str(executable)
    return env, log


def test_opt_in_adds_semantic_match_without_changing_arguments(tmp_path):
    env, log = fake_jev(tmp_path, {"ia-debugging": {"type": "noul", "noul": 0.97}})
    prompt = "Find out why yesterday's deployment now returns nothing to callers."
    assert run_hook(prompt, env) == ""
    assert not log.exists()
    env["WHETSTONE_JEV"] = "1"
    result = json.loads(run_hook(prompt, env))["hookSpecificOutput"]["updatedInput"]
    assert "ia-debugging/SKILL.md" in result["prompt"]
    assert "Jev suggests" in result["prompt"]
    assert result["prompt"].endswith("\n\n" + prompt)
    assert result["model"] == "sonnet"
    assert result["run_in_background"] is True
    request = json.loads(log.read_text())
    assert request["state"] == prompt
    assert request["questions"]["ia-debugging"]["type"] == "noul"


@pytest.mark.parametrize("setting", [None, "", "0", "false", "yes"])
def test_disabled_mode_never_calls_jev(tmp_path, setting):
    env, log = fake_jev(tmp_path, {})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    if setting is not None:
        env["WHETSTONE_JEV"] = setting
    assert run_hook(prompt, env) == original
    assert not log.exists()
    env["WHETSTONE_JEV"] = "1"
    run_hook(prompt, env)
    assert log.exists(), "Positive control must exercise this test's invocation detector"


def test_missing_cli_preserves_regex_output(tmp_path):
    env, _ = fake_jev(tmp_path, {})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    env.update(WHETSTONE_JEV="1", WHETSTONE_JEV_COMMAND=str(tmp_path / "not-installed"))
    assert run_hook(prompt, env) == original


@pytest.mark.parametrize("reply", [
    "not-json", "[]", '{"status":"error"}',
    '{"schema_version":1,"status":"ok","answers":{}}',
])
def test_invalid_cli_response_preserves_regex_output(tmp_path, reply):
    env, _ = fake_jev(tmp_path, {})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    Path(env["WHETSTONE_JEV_COMMAND"]).write_text(f"#!{sys.executable}\nprint({reply!r})\n")
    env["WHETSTONE_JEV"] = "1"
    assert run_hook(prompt, env) == original


@pytest.mark.parametrize("score", [True, None, "0.99", -0.01, 1.01])
def test_invalid_score_preserves_regex_output(tmp_path, score):
    env, _ = fake_jev(tmp_path, {"ia-writing": {"type": "noul", "noul": score}})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    env["WHETSTONE_JEV"] = "1"
    assert run_hook(prompt, env) == original


def test_threshold_is_configurable_and_regex_selections_remain_first(tmp_path):
    env, log = fake_jev(tmp_path, {"ia-writing": {"type": "noul", "noul": 0.93}})
    prompt = "Implement a Python CLI service"
    original = run_hook(prompt, env)
    env.update(WHETSTONE_JEV="1", WHETSTONE_JEV_THRESHOLD="0.95")
    assert run_hook(prompt, env) == original
    env["WHETSTONE_JEV_THRESHOLD"] = "0.90"
    updated = json.loads(run_hook(prompt, env))["hookSpecificOutput"]["updatedInput"]["prompt"]
    assert updated.index("ia-python-services/SKILL.md") < updated.index("ia-writing/SKILL.md")
    assert "Additional skill suggestions (Jev; check applicability before following):" in updated
    assert "ia-python-services" not in json.loads(log.read_text())["questions"]


@pytest.mark.parametrize("threshold", ["NaN", "Infinity", "bad", "-0.1", "1.1"])
def test_invalid_threshold_declines_before_cli(tmp_path, threshold):
    env, log = fake_jev(tmp_path, {})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    env.update(WHETSTONE_JEV="1", WHETSTONE_JEV_THRESHOLD=threshold)
    assert run_hook(prompt, env) == original
    assert not log.exists()


def test_full_regex_selection_skips_jev(tmp_path):
    env, log = fake_jev(tmp_path, {})
    prompt = "Plan this feature. Fix the bug. Review code. Refactor code. Brainstorm. Write tests. Claim fixed."
    original = run_hook(prompt, env)
    env["WHETSTONE_JEV"] = "1"
    assert run_hook(prompt, env) == original
    assert not log.exists()


def test_semantic_matches_fill_only_remaining_slots(tmp_path):
    env, _ = fake_jev(tmp_path, {
        name: {"type": "noul", "noul": 0.99}
        for name in ["ia-writing", "ia-debugging", "ia-planning", "ia-nodejs-backend", "ia-c-systems"]
    })
    env["WHETSTONE_JEV"] = "1"
    prompt = "Implement a Python CLI service"
    updated = json.loads(run_hook(prompt, env))["hookSpecificOutput"]["updatedInput"]["prompt"]
    paths = [line for line in updated.splitlines() if line.startswith("- ")]
    assert len(paths) == 5
    assert paths[0].endswith("ia-python-services/SKILL.md")
    assert all(Path(line[2:]).is_file() for line in paths)


@pytest.mark.parametrize(("prompt", "excluded"), [
    ("Inspect this C# service", "ia-c-systems"),
    ("Inspect plugins/whetstone/skills/ia-debugging/SKILL.md", "ia-debugging"),
])
def test_excluded_skills_are_never_offered_to_jev(tmp_path, prompt, excluded):
    env, log = fake_jev(tmp_path, {})
    env["WHETSTONE_JEV"] = "1"
    run_hook(prompt, env)
    assert excluded not in json.loads(log.read_text())["questions"]


@pytest.mark.parametrize("code", ["raise SystemExit(1)", "import time; time.sleep(10)"])
def test_cli_failure_or_timeout_preserves_regex_output(tmp_path, code):
    env, _ = fake_jev(tmp_path, {})
    prompt = "Fix the bug in Python CLI service"
    original = run_hook(prompt, env)
    Path(env["WHETSTONE_JEV_COMMAND"]).write_text(f"#!{sys.executable}\n{code}\n")
    env["WHETSTONE_JEV"] = "1"
    assert run_hook(prompt, env) == original


@pytest.mark.parametrize(("text", "expected"), [
    ("no frontmatter", ""),
    ("---\nname: ia-test\n---\n", ""),
    ("---\ndescription:\nclass: tool\n---\n", ""),
    ('---\ndescription: "Use for testing."\n---\n', "Use for testing."),
    ("---\ndescription: >-\n  Use for\n  testing.\nclass: tool\n---\n", "Use for testing."),
])
def test_skill_scope_is_read_from_frontmatter(tmp_path, text, expected):
    path = tmp_path / "SKILL.md"
    path.write_text(text)
    assert HELPER.description(path) == expected


@pytest.mark.parametrize(("response", "expected"), [
    ({"schema_version": 1, "status": "ok", "answers": {"ia-debugging": {"type": "noul", "noul": 0.97}}}, "ia-debugging\n"),
    ({"schema_version": 1, "status": "ok", "answers": {"ia-debugging": {"type": "noul", "noul": 0.1}}}, ""),
    ({"schema_version": 1, "status": "ok", "answers": {"ia-debugging": {"type": "noul", "noul": float("nan")}}}, ""),
    ({"schema_version": 1, "status": "ok", "answers": {"ia-debugging": {"type": "choice", "noul": 0.97}}}, ""),
    ({"schema_version": 1, "status": "ok", "answers": {"ia-debugging": None}}, ""),
    ({"schema_version": 1, "status": "ok", "answers": {}}, ""),
    ({"schema_version": 1, "status": "error"}, ""),
    ({"schema_version": True, "status": "ok", "answers": {"ia-debugging": {"type": "noul", "noul": 0.97}}}, ""),
    ({"schema_version": 1, "model": "other", "status": "ok", "answers": {"ia-debugging": {"type": "noul", "noul": 0.97}}}, ""),
    ([], ""),
])
def test_helper_validates_cli_reply(tmp_path, monkeypatch, capsys, response, expected):
    env, _ = fake_jev(tmp_path, {})
    executable = Path(env["WHETSTONE_JEV_COMMAND"])
    if isinstance(response, dict):
        response.setdefault("model", "jev-1.13.0")
    executable.write_text(f"#!{sys.executable}\nprint({json.dumps(response)!r})\n")
    monkeypatch.setenv("WHETSTONE_JEV", "1")
    monkeypatch.setenv("WHETSTONE_JEV_COMMAND", str(executable))
    monkeypatch.delenv("WHETSTONE_JEV_THRESHOLD", raising=False)
    monkeypatch.setattr(sys, "argv", ["jev-skills.py", str(PLUGIN / "skills"), "ia-debugging"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"prompt": "Find the cause."}})))
    HELPER.main()
    assert capsys.readouterr().out == expected


def test_helper_declines_disabled_empty_and_invalid_requests(tmp_path, monkeypatch, capsys):
    env, log = fake_jev(tmp_path, {})
    monkeypatch.setenv("WHETSTONE_JEV_COMMAND", env["WHETSTONE_JEV_COMMAND"])
    monkeypatch.setenv("WHETSTONE_JEV", "0")
    HELPER.main()
    monkeypatch.setenv("WHETSTONE_JEV", "1")
    assert HELPER.suggest(PLUGIN / "skills", [], "task") == []
    assert HELPER.suggest(PLUGIN / "skills", ["../escape"], "task") == []
    assert HELPER.suggest(PLUGIN / "skills", ["ia-debugging"], "") == []
    assert HELPER.suggest(PLUGIN / "skills", ["ia-debugging"], "a" * 64001) == []
    monkeypatch.setenv("WHETSTONE_JEV_THRESHOLD", "nan")
    assert HELPER.suggest(PLUGIN / "skills", ["ia-debugging"], "task") == []
    assert not log.exists()
    assert capsys.readouterr().out == ""
