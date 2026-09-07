import json
import subprocess
from pathlib import Path

import pytest

import distiller


def run_hook(tmp_path, prompt, **fields):
    payload = {
        "tool_name": "Agent",
        "hook_event_name": "PreToolUse",
        "permission_mode": "default",
        "tool_input": {"prompt": prompt, "subagent_type": "general-purpose"},
        **fields,
    }
    process = subprocess.run(
        ["bash", str(distiller.INJECT_HOOK_PATH)],
        input=json.dumps(payload), capture_output=True, text=True, cwd=tmp_path,
        timeout=5,
    )
    assert process.returncode == 0, process.stderr
    return payload, json.loads(process.stdout) if process.stdout else None


@pytest.mark.parametrize("mode", ["default", "bypassPermissions", "plan"])
@pytest.mark.parametrize("suffix", ["", "\n", "\n\n", "\u0000\n"])
def test_preserves_arguments_and_permission_policy(tmp_path, mode, suffix):
    original = {
        "prompt": "Fix the bug in Python CLI service\nKeep the literal $value and `quoted text`." + suffix,
        "subagent_type": "general-purpose", "model": "sonnet",
        "run_in_background": True, "isolation": "worktree", "nested": {"a": [1, None]},
    }
    _, result = run_hook(tmp_path, original["prompt"], tool_input=original, permission_mode=mode)
    output = result["hookSpecificOutput"]
    assert "permissionDecision" not in output
    updated = output["updatedInput"]
    assert updated["prompt"].endswith("\n\n" + original["prompt"])
    assert "ia-python-services/SKILL.md" in updated["prompt"]
    assert {k: v for k, v in updated.items() if k != "prompt"} == {
        k: v for k, v in original.items() if k != "prompt"
    }


@pytest.mark.parametrize("prompt", [
    "Implement a Python CLI service",
    "Fix the bug in distiller.py Python CLI service",
    "Fix the bug in distiller.py analyze-misfires Python CLI service",
])
def test_explicit_python_task_survives_js_repository_markers(tmp_path, prompt):
    (tmp_path / "package.json").write_text("{}")
    _, result = run_hook(tmp_path, prompt)
    assert "ia-python-services/SKILL.md" in result["hookSpecificOutput"]["updatedInput"]["prompt"]


@pytest.mark.parametrize("tool_input", [None, [], {"prompt": []}, {"prompt": "task", "subagent_type": []}])
def test_malformed_input_declines_without_rewrite(tmp_path, tool_input):
    _, result = run_hook(tmp_path, "task", tool_input=tool_input)
    assert result is None


@pytest.mark.parametrize("damage", ["invalid-json", "missing-fields", "altered-prompt", "invalid-event"])
def test_semantic_runner_rejects_broken_wire_output(tmp_path, monkeypatch, damage):
    prompt = "Fix the bug in Python CLI service"
    _, good = run_hook(tmp_path, prompt)
    if damage == "invalid-json":
        output = "INVALID JSON"
    else:
        hook = good["hookSpecificOutput"]
        if damage == "missing-fields":
            del hook["updatedInput"]["subagent_type"]
        elif damage == "altered-prompt":
            hook["updatedInput"]["prompt"] += "discarded user requirement"
        else:
            hook["hookEventName"] = "PostToolUse"
        output = json.dumps(good)
    stub = tmp_path / "broken-hook.sh"
    stub.write_text("cat <<'OUTPUT'\n" + output + "\nOUTPUT\n")
    monkeypatch.setattr(distiller, "INJECT_HOOK_PATH", stub)
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": prompt, "should_trigger": [], "should_not_trigger": []}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["summary"]["errors"] == 1


def test_semantic_runner_uses_wire_not_diagnostic_log(tmp_path, monkeypatch):
    stub = tmp_path / "silent-hook.sh"
    stub.write_text('if [ -n "${TEST_INJECTION_LOG:-}" ]; then printf "ia-debugging\\n" >>"$TEST_INJECTION_LOG"; fi\n')
    monkeypatch.setattr(distiller, "INJECT_HOOK_PATH", stub)
    monkeypatch.setenv("TEST_INJECTION_LOG", str(tmp_path / "diagnostic.log"))
    fixture = tmp_path / "fixtures.jsonl"
    fixture.write_text(json.dumps({"prompt": "Fix the bug", "should_trigger": ["ia-debugging"]}) + "\n")
    result = distiller.test_semantic(fixtures_path=fixture)
    assert result["all_passed"] is False
    assert result["results"][0]["missing"] == ["ia-debugging"]


def test_cap_and_order_are_stable(tmp_path):
    prompt = "Plan this feature. Fix the bug. Review code. Refactor code. Brainstorm. Write tests. Claim fixed."
    _, first = run_hook(tmp_path, prompt)
    _, second = run_hook(tmp_path, prompt)
    assert first == second
    paths = [line for line in first["hookSpecificOutput"]["updatedInput"]["prompt"].splitlines() if line.startswith("- ")]
    assert len(paths) == 5
    assert len(set(paths)) == 5
    assert all(Path(line[2:]).is_file() for line in paths)
