import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import distiller
import pytest


def run_hook(tmp_path, prompt, *, env=None, **fields):
    payload = {
        "session_id": "hook-test",
        "tool_use_id": "tool-test",
        "tool_name": "Agent",
        "hook_event_name": "PreToolUse",
        "permission_mode": "default",
        "tool_input": {"prompt": prompt, "subagent_type": "general-purpose"},
        **fields,
    }
    with tempfile.TemporaryDirectory(dir=tmp_path) as queue_tmp:
        hook_env = {**(env if env is not None else os.environ), "TMPDIR": queue_tmp}
        if env is None:
            hook_env["WHETSTONE_JEV"] = "0"
        process = subprocess.run(
            ["bash", str(distiller.INJECT_HOOK_PATH)],
            input=json.dumps(payload), capture_output=True, text=True, cwd=tmp_path,
            timeout=5, env=hook_env, check=False,
        )
        assert process.returncode == 0, process.stderr
        assert process.stdout == ""
        tool_input = payload.get("tool_input")
        agent_type = "general-purpose"
        if isinstance(tool_input, dict):
            agent_type = tool_input.get("subagent_type", "general-purpose")
            if isinstance(tool_input.get("prompt"), str) and isinstance(agent_type, str):
                entries = list(Path(queue_tmp).rglob("*.json"))
                assert len(entries) == 1
                assert json.loads(entries[0].read_text())["prompt"] == tool_input["prompt"]
        process = subprocess.run(
            ["bash", str(distiller.SUBAGENT_START_HOOK_PATH)],
            input=json.dumps({
                "session_id": payload["session_id"], "agent_id": "agent-test",
                "agent_type": agent_type, "hook_event_name": "SubagentStart",
                "cwd": str(tmp_path),
            }),
            capture_output=True, text=True, cwd=tmp_path,
            timeout=5, env=hook_env, check=False,
        )
        assert process.returncode == 0, process.stderr
        return payload, json.loads(process.stdout) if process.stdout else None


@pytest.mark.parametrize("mode", ["default", "bypassPermissions", "plan"])
@pytest.mark.parametrize("suffix", ["", "\n", "\n\n", "\u0000\n"])
def test_records_exact_prompt_without_emitting_a_tool_decision(tmp_path, mode, suffix):
    original = {
        "prompt": "Fix the bug in Python CLI service\nKeep the literal $value and `quoted text`." + suffix,
        "subagent_type": "general-purpose", "model": "sonnet",
        "run_in_background": True, "isolation": "worktree", "nested": {"a": [1, None]},
    }
    _, result = run_hook(tmp_path, original["prompt"], tool_input=original, permission_mode=mode)
    output = result["hookSpecificOutput"]
    assert set(output) == {"hookEventName", "additionalContext"}
    assert output["hookEventName"] == "SubagentStart"
    assert "ia-python-services/SKILL.md" in output["additionalContext"]
    assert original["prompt"] not in output["additionalContext"]


@pytest.mark.parametrize("prompt", [
    "Implement a Python CLI service",
    "Fix the bug in distiller.py Python CLI service",
    "Fix the bug in distiller.py analyze-misfires Python CLI service",
])
def test_explicit_python_task_survives_js_repository_markers(tmp_path, prompt):
    (tmp_path / "package.json").write_text("{}")
    _, result = run_hook(tmp_path, prompt)
    assert "ia-python-services/SKILL.md" in result["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("trigger_first", [True, False])
def test_large_prompt_matches_at_either_end(tmp_path, trigger_first):
    trigger = "Implement a Python CLI service"
    padding = "x" * 160_000
    prompt = f"{trigger}\n{padding}" if trigger_first else f"{padding}\n{trigger}"
    _, result = run_hook(tmp_path, prompt)
    assert result is not None
    assert "ia-python-services/SKILL.md" in result["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(("marker", "trigger", "excluded"), [
    ("Inspect plugins/whetstone/skills/ia-debugging/SKILL.md", "Fix the bug", "ia-debugging"),
    ("Inspect this C# service", "Fix a segfault", "ia-c-systems"),
])
def test_large_prompt_preserves_exclusions(tmp_path, marker, trigger, excluded):
    _, result = run_hook(tmp_path, marker + "\n" + "x" * 160_000 + "\n" + trigger)
    context = result["hookSpecificOutput"]["additionalContext"] if result else ""
    assert f"{excluded}/SKILL.md" not in context


def test_queue_suggestions_require_actual_task_check(tmp_path):
    _, result = run_hook(tmp_path, "Implement a Python CLI service")
    context = result["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("BEFORE STARTING: These skill files matched your task description")
    assert "confirm each applies to your actual task" in context
    assert "Read and follow these skill files" not in context
    assert distiller._extract_injected_skills(context) == [{"skill": "ia-python-services", "version": None}]
    assert distiller._strip_injection_header(context + "\nActual task") == "Actual task"


@pytest.mark.parametrize("tool_input", [None, [], {"prompt": []}, {"prompt": "task", "subagent_type": []}])
def test_malformed_input_declines_without_rewrite(tmp_path, tool_input):
    _, result = run_hook(tmp_path, "task", tool_input=tool_input)
    assert result is None


@pytest.mark.parametrize("damage", [
    "invalid-json", "missing-fields", "invalid-context", "oversized-context",
    "invalid-event", "unexpected-field",
])
def test_semantic_runner_rejects_broken_wire_output(tmp_path, monkeypatch, damage):
    prompt = "Fix the bug in Python CLI service"
    _, good = run_hook(tmp_path, prompt)
    if damage == "invalid-json":
        output = "INVALID JSON"
    else:
        hook = good["hookSpecificOutput"]
        if damage == "missing-fields":
            del hook["additionalContext"]
        elif damage == "invalid-context":
            hook["additionalContext"] = []
        elif damage == "oversized-context":
            hook["additionalContext"] += "x" * 10001
        elif damage == "unexpected-field":
            hook["permissionDecision"] = "allow"
        elif damage == "invalid-event":
            hook["hookEventName"] = "PostToolUse"
        output = json.dumps(good)
    stub = tmp_path / "broken-hook.sh"
    stub.write_text("cat <<'OUTPUT'\n" + output + "\nOUTPUT\n")
    monkeypatch.setattr(distiller, "SUBAGENT_START_HOOK_PATH", stub)
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": prompt, "should_trigger": [], "should_not_trigger": []}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["summary"]["errors"] == 1


@pytest.mark.parametrize("output", [" ", '{"hookSpecificOutput":{}}'])
def test_semantic_runner_rejects_any_recorder_output(tmp_path, monkeypatch, output):
    stub = tmp_path / "noisy-recorder.sh"
    stub.write_text("cat <<'OUTPUT'\n" + output + "\nOUTPUT\n")
    monkeypatch.setattr(distiller, "INJECT_HOOK_PATH", stub)
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": "A task", "should_trigger": []}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["summary"]["errors"] == 1


@pytest.mark.parametrize("hook_name", ["INJECT_HOOK_PATH", "SUBAGENT_START_HOOK_PATH"])
def test_semantic_runner_rejects_crashing_hooks(tmp_path, monkeypatch, hook_name):
    stub = tmp_path / "crashing-hook.sh"
    stub.write_text("exit 1\n")
    monkeypatch.setattr(distiller, hook_name, stub)
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": "A task", "should_trigger": []}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["summary"]["errors"] == 1


def test_semantic_runner_uses_wire_not_diagnostic_log(tmp_path, monkeypatch):
    stub = tmp_path / "silent-hook.sh"
    stub.write_text('if [ -n "${TEST_INJECTION_LOG:-}" ]; then printf "ia-debugging\\n" >>"$TEST_INJECTION_LOG"; fi\n')
    monkeypatch.setattr(distiller, "SUBAGENT_START_HOOK_PATH", stub)
    monkeypatch.setenv("TEST_INJECTION_LOG", str(tmp_path / "diagnostic.log"))
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": "Fix the bug", "should_trigger": ["ia-debugging"]}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["results"][0]["missing"] == ["ia-debugging"]
    assert (tmp_path / "diagnostic.log").read_text() == "ia-debugging\n"


def test_cap_and_order_are_stable(tmp_path):
    prompt = "Plan this feature. Fix the bug. Review code. Refactor code. Brainstorm. Write tests. Claim fixed."
    _, first = run_hook(tmp_path, prompt)
    _, second = run_hook(tmp_path, prompt)
    assert first == second
    paths = [line for line in first["hookSpecificOutput"]["additionalContext"].splitlines() if line.startswith("- ")]
    assert len(paths) == 5
    assert len(set(paths)) == 5
    assert all(Path(line[2:]).is_file() for line in paths)


def test_semantic_runner_never_calls_opted_in_jev(tmp_path, monkeypatch):
    marker = tmp_path / "jev-called"
    executable = tmp_path / "jev"
    executable.write_text(
        f"#!{sys.executable}\nfrom pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('called')\nraise SystemExit(1)\n"
    )
    executable.chmod(0o700)
    monkeypatch.setenv("WHETSTONE_JEV", "1")
    monkeypatch.setenv("WHETSTONE_JEV_COMMAND", str(executable))
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": "Fix the bug", "should_trigger": ["ia-debugging"]}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is True
    assert not marker.exists()
    run_hook(tmp_path, "Fix the bug", env=os.environ.copy())
    assert marker.exists(), "Positive control must observe the opted-in CLI invocation"
