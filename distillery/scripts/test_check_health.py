import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "whetstone"
TOOLS = (
    "bash", "git", "jq", "python3", "gh", "grep", "dirname", "cat", "mkdir",
    "stat", "find", "tr", "sort", "mv", "date", "rm", "mktemp", "readlink",
)


def link_tool(bin_dir, name, source=None):
    target = shutil.which(source or name)
    assert target is not None, f"Test dependency unavailable: {source or name}"
    (bin_dir / name).symlink_to(target)


@pytest.fixture
def health_env(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in TOOLS:
        link_tool(bin_dir, name)
    link_tool(bin_dir, "claude", "true")
    return {
        "PATH": str(bin_dir),
        "TMPDIR": str(tmp_path),
        "WHETSTONE_JEV": "0",
    }


def run_bash(env, *args, payload=None, interpreter=None):
    result = subprocess.run(
        [str(interpreter or Path(env["PATH"]) / "bash"), *map(str, args)],
        input=None if payload is None else json.dumps(payload),
        capture_output=True, text=True, env=env, cwd=env["TMPDIR"], timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return result.stdout


@pytest.mark.parametrize("path_version, supported", [("4.3", False), ("4.4", True), ("5.0", True)])
def test_health_uses_bash_version_from_path(health_env, path_version, supported):
    bin_dir = Path(health_env["PATH"])
    link_tool(bin_dir, "flock")
    path_bash = bin_dir / "bash"
    interpreter = path_bash.resolve()
    path_bash.unlink()
    path_bash.write_text(f"#!/bin/sh\nprintf '%s\\n' '{path_version}'\n")
    path_bash.chmod(0o700)

    health = run_bash(health_env, PLUGIN / "scripts/check-health.sh", interpreter=interpreter)

    if supported:
        assert f"bash ({path_version})" in health
        assert "All clear" in health
    else:
        assert f"Bash on PATH reported version {path_version}." in health
        assert "Automatic skill injection requires Bash 4.4 or newer on PATH." in health
        assert "1 issue(s) found" in health
        assert "All clear" not in health


def test_missing_flock_health_matches_actual_injection(health_env):
    health = run_bash(health_env, PLUGIN / "scripts/check-health.sh")
    assert "issue(s) found" in health
    assert "All clear" not in health
    assert "Automatic skill injection unavailable: flock is missing." in health

    record = {
        "session_id": "health-check", "tool_use_id": "tool-1",
        "tool_input": {"subagent_type": "general-purpose", "prompt": "write Python CLI"},
    }
    start = {
        "session_id": "health-check", "agent_type": "general-purpose",
        "agent_id": "agent-1", "hook_event_name": "SubagentStart",
    }
    assert run_bash(health_env, PLUGIN / "hooks/inject-skills.sh", payload=record) == ""
    assert run_bash(health_env, PLUGIN / "hooks/subagent-start.sh", payload=start) == ""

    link_tool(Path(health_env["PATH"]), "flock")
    assert "All clear" in run_bash(health_env, PLUGIN / "scripts/check-health.sh")
    assert run_bash(health_env, PLUGIN / "hooks/inject-skills.sh", payload=record) == ""
    output = run_bash(health_env, PLUGIN / "hooks/subagent-start.sh", payload=start)
    context = json.loads(output)["hookSpecificOutput"]["additionalContext"]
    assert "ia-python-services/SKILL.md" in context


@pytest.mark.parametrize("package_manager", ["apt-get", "brew", None])
def test_install_commands_are_distinct_from_manual_urls(health_env, package_manager):
    bin_dir = Path(health_env["PATH"])
    (bin_dir / "gh").unlink()
    if package_manager is not None:
        link_tool(bin_dir, package_manager, "true")
    health = run_bash(health_env, PLUGIN / "scripts/check-health.sh")
    assert "Install command: https://" not in health
    assert "Install command: http://" not in health
    if package_manager == "apt-get":
        assert "Manual instructions: https://github.com/cli/cli/blob/trunk/docs/install_linux.md" in health
        assert "Install command: sudo apt install -y util-linux" in health
    elif package_manager == "brew":
        assert "Install command: brew install gh" in health
        assert "Manual instructions: https://github.com/util-linux/util-linux" in health
    else:
        assert "Install command:" not in health
        assert "Manual instructions: https://cli.github.com" in health


def test_setup_health_recipes_support_spaces(health_env):
    plugin = Path(health_env["TMPDIR"]) / "plugin space"
    plugin.symlink_to(PLUGIN, target_is_directory=True)
    env = {**health_env, "CLAUDE_PLUGIN_ROOT": str(plugin)}
    command = (PLUGIN / "commands/ia-setup.md").read_text()
    recipes = [
        body.strip()
        for body in re.findall(r"```bash\n(.*?)\n```", command, re.S)
        if "/scripts/check-health.sh" in body
    ]
    assert len(recipes) == 2
    for recipe in recipes:
        health = run_bash(env, "-c", recipe)
        assert "issue(s) found" in health
        if "--version" in recipe:
            assert "Plugin version vVERSION" in health


@pytest.mark.parametrize(
    "manifests, stack",
    [
        ((), "general"),
        (("package.json",), "javascript"),
        (("composer.json",), "php"),
        (("requirements.txt", "composer.json"), "python"),
        (("tsconfig.json", "package.json"), "typescript"),
    ],
)
def test_setup_detects_one_stack(health_env, manifests, stack):
    for manifest in manifests:
        (Path(health_env["TMPDIR"]) / manifest).touch()
    command = (PLUGIN / "commands/ia-setup.md").read_text()
    section = command.split("### Step 6: Detect Stack", 1)[1]
    detector = re.search(r"```bash\n(.*?)\n```", section, re.S).group(1)
    assert run_bash(health_env, "-c", detector) == f"{stack}\n"
