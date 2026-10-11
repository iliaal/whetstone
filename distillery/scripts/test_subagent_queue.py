import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "whetstone"


@pytest.fixture
def queue_env(tmp_path):
    return {**os.environ, "TMPDIR": str(tmp_path), "WHETSTONE_JEV": "0"}


def queue_dir(env, session="session"):
    return Path(env["TMPDIR"]) / f"whetstone-subagent-queue-{os.getuid()}" / session


def run_hook(script, payload, env, plugin=PLUGIN):
    result = subprocess.run(
        ["bash", str(plugin / "hooks" / script)],
        input=json.dumps(payload), text=True, capture_output=True, env=env,
        cwd=env["TMPDIR"], timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return result.stdout


def record(env, prompt, agent="general-purpose", tool="tool", session="session", plugin=PLUGIN):
    assert run_hook("inject-skills.sh", {
        "session_id": session, "tool_use_id": tool, "hook_event_name": "PreToolUse",
        "tool_input": {"prompt": prompt, "subagent_type": agent},
    }, env, plugin) == ""


def start(env, agent="general-purpose", session="session", plugin=PLUGIN):
    output = run_hook("subagent-start.sh", {
        "session_id": session, "agent_id": "agent", "agent_type": agent,
        "hook_event_name": "SubagentStart",
    }, env, plugin)
    if not output:
        return ""
    body = json.loads(output)
    assert set(body) == {"hookSpecificOutput"}
    assert set(body["hookSpecificOutput"]) == {"hookEventName", "additionalContext"}
    assert body["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    return body["hookSpecificOutput"]["additionalContext"]


def finish(env, event, tool="tool", session="session", tool_name="Agent"):
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    for group in hooks.get(event, []):
        if not re.fullmatch(group["matcher"], tool_name):
            continue
        for hook in group["hooks"]:
            command = hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN))
            result = subprocess.run(
                shlex.split(command), input=json.dumps({
                    "session_id": session, "tool_use_id": tool, "tool_name": tool_name,
                    "hook_event_name": event,
                }), text=True, capture_output=True, env=env, cwd=env["TMPDIR"], timeout=10,
            )
            assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("event", ["PostToolUseFailure", "PermissionDenied"])
@pytest.mark.parametrize("tool_name", ["Agent", "Task"])
def test_failed_or_denied_call_cannot_supply_next_context(queue_env, event, tool_name):
    record(queue_env, "write Python CLI", tool="denied")
    record(queue_env, "build Laravel controller", tool="next")
    finish(queue_env, event, tool="denied", tool_name=tool_name)
    context = start(queue_env)
    assert "ia-php-laravel/SKILL.md" in context
    assert "ia-python-services/SKILL.md" not in context
    assert start(queue_env) == ""


@pytest.mark.parametrize("event", ["PostToolUseFailure", "PermissionDenied"])
def test_cleanup_matches_complete_call_id_and_session(queue_env, event):
    record(queue_env, "write Python CLI", tool="prefix-tool")
    record(queue_env, "implement Rust CLI", tool="tool", session="other")
    record(queue_env, "build Laravel controller", tool="tool")
    finish(queue_env, event)
    assert "ia-python-services/SKILL.md" in start(queue_env)
    assert start(queue_env) == ""
    assert "ia-rust-systems/SKILL.md" in start(queue_env, session="other")


@pytest.mark.parametrize("event", ["PostToolUseFailure", "PermissionDenied"])
def test_cleanup_after_claim_leaves_other_pending_calls(queue_env, event):
    record(queue_env, "write Python CLI")
    assert "ia-python-services/SKILL.md" in start(queue_env)
    record(queue_env, "build Laravel controller", tool="next")
    finish(queue_env, event)
    finish(queue_env, event)
    assert "ia-php-laravel/SKILL.md" in start(queue_env)


@pytest.mark.parametrize(("field", "value"), [
    ("tool_use_id", ""), ("tool_use_id", "../tool"), ("tool_use_id", "*"),
    ("tool_use_id", None), ("tool_use_id", []), ("tool_use_id", "tool\n"),
    ("session_id", "../session"), ("session_id", None),
    ("hook_event_name", "PermissionRequest"), ("hook_event_name", "PreToolUse"),
    ("tool_name", "Bash"),
])
def test_cleanup_rejects_uncorrelated_events(queue_env, field, value):
    record(queue_env, "write Python CLI")
    payload = {
        "session_id": "session", "tool_use_id": "tool", "tool_name": "Agent",
        "hook_event_name": "PostToolUseFailure", field: value,
    }
    assert run_hook("discard-subagent.sh", payload, queue_env) == ""
    assert "ia-python-services/SKILL.md" in start(queue_env)


def test_private_queue_and_default_type(queue_env):
    run_hook("inject-skills.sh", {
        "session_id": "session", "tool_use_id": "tool", "tool_input": {"prompt": "write Python CLI"},
    }, queue_env)
    directory = queue_dir(queue_env)
    assert directory.stat().st_mode & 0o777 == 0o700
    assert directory.parent.stat().st_mode & 0o777 == 0o700
    files = list(directory.glob("*.json"))
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    entry = json.loads(files[0].read_text())
    assert entry == {"subagent_type": "general-purpose", "prompt": "write Python CLI",
                     "skills": ["ia-python-services"], "enqueued_at": entry["enqueued_at"]}
    assert abs(time.time() - entry["enqueued_at"]) < 10
    assert "ia-python-services/SKILL.md" in start(queue_env)
    assert not list(directory.glob("*.json"))


@pytest.mark.parametrize("script", ["inject-skills.sh", "subagent-start.sh", "discard-subagent.sh"])
@pytest.mark.parametrize("payload", ["{", "null", "[]", "1", '"input"'])
def test_malformed_input_fails_open(queue_env, script, payload):
    result = subprocess.run(["bash", str(PLUGIN / "hooks" / script)], input=payload,
                            text=True, capture_output=True, env=queue_env, timeout=10)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("identifier", ["../escape", ".", "..", "/absolute", "bad/id", "x\n", "", "a" * 129])
@pytest.mark.parametrize("field", ["session_id", "tool_use_id"])
def test_invalid_ids_rejected(queue_env, field, identifier):
    payload = {"session_id": "session", "tool_use_id": "tool", "tool_input": {"prompt": "write Python CLI"}}
    payload[field] = identifier
    assert run_hook("inject-skills.sh", payload, queue_env) == ""
    assert not list(Path(queue_env["TMPDIR"]).rglob("*.json"))
    if field == "session_id":
        assert start(queue_env, session=identifier) == ""


def test_queue_creation_error_fails_open(queue_env):
    Path(queue_env["TMPDIR"], f"whetstone-subagent-queue-{os.getuid()}").write_text("occupied")
    record(queue_env, "write Python CLI")
    assert start(queue_env) == ""


@pytest.mark.parametrize("script", ["inject-skills.sh", "subagent-start.sh", "discard-subagent.sh"])
def test_missing_dependencies_fail_open(queue_env, script):
    env = {**queue_env, "PATH": queue_env["TMPDIR"]}
    result = subprocess.run(["/bin/bash", str(PLUGIN / "hooks" / script)], input="{}",
                            text=True, capture_output=True, env=env, timeout=10)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_symlink_queue_rejected(queue_env, tmp_path):
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    queue_dir(queue_env).parent.symlink_to(target, target_is_directory=True)
    record(queue_env, "write Python CLI")
    assert not list(target.iterdir())


def test_type_routing_and_same_type_batch_union(queue_env):
    record(queue_env, "write Python CLI", "whetstone:ia-security-sentinel", "first")
    record(queue_env, "implement Rust CLI", "Explore", "second")
    record(queue_env, "build Laravel controller", "ia-security-sentinel", "third")
    assert start(queue_env, "Plan") == ""
    explore = start(queue_env, "Explore")
    assert "ia-rust-systems/SKILL.md" in explore
    assert "started together" not in explore
    for _ in range(2):
        context = start(queue_env, "ia-security-sentinel")
        assert "started together" in context
        assert "ia-python-services/SKILL.md" in context
        assert "ia-php-laravel/SKILL.md" in context
    assert start(queue_env, "whetstone:ia-security-sentinel") == ""
    assert not list(queue_dir(queue_env).glob("*.json"))
    assert not list(queue_dir(queue_env).glob(".used-*"))


@pytest.mark.parametrize("order", ["forward", "reverse"])
def test_parallel_same_type_starts_each_receive_own_context(queue_env, order):
    record(queue_env, "write Python CLI", tool="tool-a")
    record(queue_env, "build Laravel controller", tool="tool-b")
    first, second = start(queue_env), start(queue_env)
    contexts = [first, second] if order == "forward" else [second, first]
    for context in contexts:
        assert "ia-python-services/SKILL.md" in context
        assert "ia-php-laravel/SKILL.md" in context
    assert not list(queue_dir(queue_env).glob(".used-*"))
    record(queue_env, "build Laravel controller", tool="tool-c")
    context = start(queue_env)
    assert "ia-php-laravel/SKILL.md" in context
    assert "ia-python-services/SKILL.md" not in context
    assert "started together" not in context


def test_leftover_entry_does_not_blank_next_start(queue_env):
    record(queue_env, "write Python CLI", tool="orphan")
    record(queue_env, "build Laravel controller", tool="fresh")
    assert "ia-php-laravel/SKILL.md" in start(queue_env)


def test_other_plugin_namespace_and_session_stay_distinct(queue_env):
    record(queue_env, "write Python CLI", "other:ia-security-sentinel")
    assert start(queue_env, "whetstone:ia-security-sentinel") == ""
    assert start(queue_env, "other:ia-security-sentinel", session="other-session") == ""
    assert "ia-python-services/SKILL.md" in start(queue_env, "other:ia-security-sentinel")


@pytest.mark.parametrize("hook", ["record", "start"])
def test_stale_entries_pruned_across_sessions(queue_env, hook):
    record(queue_env, "write Python CLI", session="abandoned")
    record(queue_env, "implement Rust CLI", tool="fresh")
    stale = next(queue_dir(queue_env, "abandoned").glob("*.json"))
    old = time.time() - 901
    os.utime(stale, (old, old))
    if hook == "record":
        record(queue_env, "write Python CLI", tool="second-fresh")
    else:
        start(queue_env)
    assert not stale.exists()


def test_session_cap_drops_oldest(queue_env):
    for index in range(66):
        record(queue_env, f"entry {index}", tool=f"tool-{index}")
    entries = sorted(queue_dir(queue_env).glob("*.json"))
    assert len(entries) == 64
    assert [json.loads(file.read_text())["prompt"] for file in entries] == [f"entry {i}" for i in range(2, 66)]


def test_parallel_recorders_publish_every_entry(queue_env):
    count = 64
    with ThreadPoolExecutor(max_workers=count) as pool:
        list(pool.map(lambda i: record(queue_env, f"entry {i}", tool=f"tool-{i}"), range(count)))
    entries = list(queue_dir(queue_env).glob("*.json"))
    assert len(entries) == count
    assert {json.loads(file.read_text())["prompt"] for file in entries} == {f"entry {i}" for i in range(count)}
    assert not list(queue_dir(queue_env).glob(".pending-*"))


def make_fixture_plugin(root, count):
    shutil.copytree(PLUGIN / "hooks", root / "hooks")
    patterns = ["declare -A SKILL_PATTERNS SKILL_TIERS SKILL_NEGATIVE SKILL_MAINT_SUPPRESS"]
    for index in range(count):
        name = f"ia-queue-{index}"
        skill = root / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("Fixture skill\n")
        patterns += [f"SKILL_PATTERNS[{name}]='token{index}end'", f"SKILL_TIERS[{name}]=1"]
    (root / "hooks" / "skill-patterns.sh").write_text("\n".join(patterns) + "\n")
    return root


def test_concurrent_claims_are_exactly_once(queue_env, tmp_path):
    count = 12
    plugin = make_fixture_plugin(tmp_path / "plugin", count)
    for index in range(count):
        record(queue_env, f"token{index}end", f"agent-{index}", f"tool-{index}", plugin=plugin)
    with ThreadPoolExecutor(max_workers=count) as pool:
        contexts = list(pool.map(lambda i: start(queue_env, f"agent-{i}", plugin=plugin), range(count)))
    for index, context in enumerate(contexts):
        assert [line.split("/skills/")[1] for line in context.splitlines() if "/skills/" in line] == [
            f"ia-queue-{index}/SKILL.md"]
    assert not list(queue_dir(queue_env).glob("*.json"))
    assert not list(queue_dir(queue_env).glob(".claimed-*"))
    assert start(queue_env, "agent-0", plugin=plugin) == ""


def test_concurrent_same_type_starts_each_receive_whole_batch(queue_env, tmp_path):
    count = 12
    plugin = make_fixture_plugin(tmp_path / "plugin", count)
    for index in range(count):
        record(queue_env, f"token{index}end", tool=f"tool-{index}", plugin=plugin)
    with ThreadPoolExecutor(max_workers=count) as pool:
        contexts = list(pool.map(lambda _: start(queue_env, plugin=plugin), range(count)))
    expected = {f"ia-queue-{index}/SKILL.md" for index in range(count)}
    for context in contexts:
        assert {line.split("/skills/")[1] for line in context.splitlines() if "/skills/" in line} == expected
    assert not list(queue_dir(queue_env).glob("*.json"))
    assert not list(queue_dir(queue_env).glob(".used-*"))
    assert not list(queue_dir(queue_env).glob(".claimed-*"))


def test_additional_context_is_capped(queue_env, tmp_path):
    root = tmp_path
    for _ in range(9):
        root /= "p" * 200
    plugin = make_fixture_plugin(root / "plugin", 5)
    record(queue_env, " ".join(f"token{i}end" for i in range(5)), plugin=plugin)
    context = start(queue_env, plugin=plugin)
    assert len(context) == 8000
    assert context.startswith("BEFORE STARTING:")


def test_no_match_consumes_entry_without_output(queue_env):
    record(queue_env, "What is 2 + 2?")
    assert start(queue_env) == ""
    assert not list(queue_dir(queue_env).glob("*.json"))


def test_hook_scripts_cannot_rewrite_or_approve_calls():
    hooks = PLUGIN / "hooks"
    files = [hooks / "hooks.json", *hooks.glob("*.sh"), *hooks.glob("*.py")]
    result = subprocess.run(["grep", "-nE", "updatedInput|permissionDecision", *map(str, files)],
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 1, result.stdout + result.stderr


def test_bash_agent_record_stores_no_matches(queue_env):
    record(queue_env, "write Python CLI", "Bash")
    entry = json.loads(next(queue_dir(queue_env).glob("*.json")).read_text())
    assert entry["skills"] == []
    assert start(queue_env, "Bash") == ""


def test_start_uses_stored_matches(queue_env):
    record(queue_env, "write Python CLI")
    entry_file = next(queue_dir(queue_env).glob("*.json"))
    entry = json.loads(entry_file.read_text())
    entry["skills"] = ["ia-php-laravel", "../escape", "ia-not-installed"]
    entry_file.write_text(json.dumps(entry))
    context = start(queue_env)
    assert "ia-php-laravel/SKILL.md" in context
    assert "ia-python-services/SKILL.md" not in context
    assert "escape" not in context and "ia-not-installed" not in context


@pytest.mark.parametrize("batch", [False, True])
def test_legacy_record_without_skills_matches_at_start(queue_env, batch):
    record(queue_env, "write Python CLI", tool="legacy")
    if batch:
        record(queue_env, "implement Rust CLI", tool="current")
    legacy = next(queue_dir(queue_env).glob("*-legacy.json"))
    entry = json.loads(legacy.read_text())
    del entry["skills"]
    legacy.write_text(json.dumps(entry))
    context = start(queue_env)
    assert "ia-python-services/SKILL.md" in context
    assert ("ia-rust-systems/SKILL.md" in context) == batch
    assert ("started together" in context) == batch


def test_full_batch_start_with_real_patterns_is_within_timeout(queue_env):
    timeout = next(hook["timeout"] for group in json.loads((PLUGIN / "hooks" / "hooks.json").read_text())[
        "hooks"]["SubagentStart"] for hook in group["hooks"])
    prompts = ["write Python CLI with pytest", "build Laravel controller", "implement Rust CLI",
               "debug the failing React component test", "plan the terraform module"]
    count = 64
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(lambda i: record(queue_env, f"{prompts[i % len(prompts)]} {i}", tool=f"tool-{i}"),
                      range(count)))
    assert len(list(queue_dir(queue_env).glob("*.json"))) == count
    began = time.monotonic()
    context = start(queue_env)
    elapsed = time.monotonic() - began
    assert elapsed < timeout / 2, elapsed
    assert "started together" in context
    for skill in ["ia-python-services", "ia-php-laravel", "ia-rust-systems", "ia-terraform"]:
        assert f"{skill}/SKILL.md" in context


def test_discard_waits_for_queue_lock(queue_env):
    record(queue_env, "write Python CLI")
    lock = queue_dir(queue_env) / ".lock"
    holder = subprocess.Popen(["flock", str(lock), "sleep", "1"])
    try:
        time.sleep(0.2)
        began = time.monotonic()
        finish(queue_env, "PostToolUseFailure")
        assert time.monotonic() - began >= 0.5
    finally:
        holder.wait(timeout=10)
    assert not list(queue_dir(queue_env).glob("*.json"))


def test_claim_tolerates_record_removed_by_concurrent_cleanup(queue_env, tmp_path):
    for index in range(3):
        record(queue_env, ["write Python CLI", "build Laravel controller", "implement Rust CLI"][index],
               tool=f"tool-{index}")
    vanishing = next(queue_dir(queue_env).glob("*-tool-1.json"))
    shim = tmp_path / "bin"
    shim.mkdir()
    real_jq = shutil.which("jq")
    # Deletes the record after the claim enumerated it and before jq opens it.
    (shim / "jq").write_text(
        "#!/bin/bash\n"
        f"for arg; do [[ $arg == {shlex.quote(str(vanishing))} ]] && rm -f -- \"$arg\"; done\n"
        f'exec {shlex.quote(real_jq)} "$@"\n')
    (shim / "jq").chmod(0o755)
    env = {**queue_env, "PATH": f"{shim}:{queue_env['PATH']}"}
    context = start(env)
    assert "started together" in context
    assert "ia-python-services/SKILL.md" in context
    assert "ia-rust-systems/SKILL.md" in context
    assert "ia-php-laravel/SKILL.md" not in context
    assert "ia-python-services/SKILL.md" in start(env)
    assert start(env) == ""
