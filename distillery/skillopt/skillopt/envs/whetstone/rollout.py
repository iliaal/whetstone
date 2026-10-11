"""Whetstone rollout -- agentic debugging via the Claude Code exec backend.

For each fixture task: render the candidate skill into a workspace, copy the
buggy code + failing test in, run Claude Code (Read/Edit/Write/Bash, multi-turn)
to fix it, then score with the hybrid evaluator (deterministic hard + rubric
soft). Resume-aware; parallel via ThreadPoolExecutor.

Mirrors the structure of the upstream searchqa rollout, adapted from a
single-turn QA agent to a multi-turn, file-editing debug agent.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable

from skillopt.model import chat_optimizer, is_target_exec_backend
from skillopt.model.codex_harness import prepare_workspace, render_skill_md, run_target_exec

from .evaluator import evaluate, run_hard
from .rubric import Rubric, SoftGates, validate_soft_gates

_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git")


_SNAPSHOT_SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", ".git"})

# Names never taken from the agent's workspace: anything pytest or the
# interpreter loads implicitly, so the agent cannot change how its fix is graded.
_OVERLAY_DENY_NAMES = frozenset({
    "conftest.py", "pytest.ini", ".pytest.ini", "pyproject.toml", "setup.cfg",
    "tox.ini", "sitecustomize.py", "usercustomize.py",
})

# First digest observed per fixture path in this process. A later mismatch means
# the host fixture changed mid-run (e.g. a target wrote to it by absolute path),
# so it can no longer be treated as the pristine oracle.
_PINNED_FIXTURES: dict[str, str] = {}
_PINNED_LOCK = threading.Lock()


class FixtureIntegrityError(RuntimeError):
    """The host fixture no longer matches the bytes it had when first read."""


def _snapshot_fixture(fixture_dir: str) -> dict[str, bytes]:
    """Read every fixture file into memory, keyed by '/'-separated relpath.

    Bytecode and cache directories are skipped. Symlinks and other non-regular
    entries are rejected rather than followed, so the snapshot can only contain
    bytes that physically live under the fixture."""
    root = os.path.realpath(fixture_dir)
    if not os.path.isdir(root):
        raise FileNotFoundError(f"fixture dir not found: {fixture_dir}")
    out: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        keep = []
        for d in sorted(dirnames):
            if d in _SNAPSHOT_SKIP_DIRS:
                continue
            if os.path.islink(os.path.join(dirpath, d)):
                raise ValueError(f"fixture contains a symlinked directory: {os.path.join(dirpath, d)}")
            keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            if name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            st = os.lstat(full)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError(f"fixture contains a non-regular file: {full}")
            with open(full, "rb") as f:
                out[os.path.relpath(full, root).replace(os.sep, "/")] = f.read()
    return out


def _tree_digest(snapshot: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for rel in sorted(snapshot):
        data = snapshot[rel]
        h.update(rel.encode("utf-8") + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def _pin_fixture(fixture_dir: str, digest: str) -> None:
    key = os.path.realpath(fixture_dir)
    with _PINNED_LOCK:
        pinned = _PINNED_FIXTURES.setdefault(key, digest)
    if pinned != digest:
        raise FixtureIntegrityError(
            f"fixture {fixture_dir} changed since first read in this process "
            f"(pinned sha256 {pinned[:12]}, now {digest[:12]}); restore it before grading"
        )


def _is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _overlay_eligible(rel: str) -> bool:
    """A fixture file whose agent-edited version is graded: non-test, and not a
    file pytest or the interpreter loads implicitly."""
    name = rel.rsplit("/", 1)[-1]
    if _is_test_path(rel) or name in _OVERLAY_DENY_NAMES or name.endswith(".pth"):
        return False
    return True


def _read_agent_file(work_dir: str, rel: str) -> bytes | None:
    """The agent's version of a fixture file, or None when it is absent or is
    not a regular file reached without symlinks inside work_dir."""
    root = os.path.realpath(work_dir)
    path = os.path.join(root, *rel.split("/"))
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode) or os.path.realpath(path) != path:
        return None
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


# Import names a new workspace file may not take: the harness's own modules and
# the standard library, any of which pytest may import after it has put a
# workspace directory on sys.path.
_SHADOW_DENY_PREFIXES = ("pytest", "_pytest", "pluggy", "iniconfig", "_distutils_hack")
_SHADOW_DENY_NAMES = frozenset({"py", "packaging", "exceptiongroup", "tomli", "colorama",
                                "pygments", "setuptools", "pkg_resources", "xdist"})
_STDLIB_NAMES = frozenset(getattr(sys, "stdlib_module_names", ())) | frozenset(sys.builtin_module_names)

_NEW_FILE_MAX_COUNT = 50
_NEW_FILE_MAX_BYTES = 256 * 1024
_NEW_FILE_MAX_TOTAL = 1024 * 1024
_NEW_FILE_SCAN_LIMIT = 2000


def _new_file_eligible(rel: str, test_dirs: set[str]) -> bool:
    """An agent-created file (absent from the fixture) that may join grading:
    a non-hidden .py source that is not a test, not implicitly loaded by pytest
    or the interpreter, cannot shadow the harness or stdlib by import name, and
    is not an __init__.py that would change how a fixture test is imported."""
    parts = rel.split("/")
    name = parts[-1]
    if not name.endswith(".py") or _is_test_path(rel) or not _overlay_eligible(rel):
        return False
    if any(p.startswith(".") for p in parts):
        return False
    if name == "__init__.py" and "/".join(parts[:-1]) in test_dirs:
        return False
    for seg in parts[:-1] + [name[:-3]]:
        if seg in _STDLIB_NAMES or seg in _SHADOW_DENY_NAMES or seg.startswith(_SHADOW_DENY_PREFIXES):
            return False
    return True


def _new_agent_files(snapshot: dict[str, bytes], work_dir: str) -> dict[str, bytes]:
    """Eligible files the agent created, or nothing when the set exceeds the
    count/size limits (a partial set would make grading depend on walk order)."""
    root = os.path.realpath(work_dir)
    if not os.path.isdir(root):
        return {}
    test_dirs = {rel.rsplit("/", 1)[0] if "/" in rel else "" for rel in snapshot if _is_test_path(rel)}
    found: dict[str, bytes] = {}
    total = 0
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _SNAPSHOT_SKIP_DIRS and not d.startswith(".")
                             and not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(filenames):
            scanned += 1
            if scanned > _NEW_FILE_SCAN_LIMIT:
                return {}
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            if rel in snapshot or not _new_file_eligible(rel, test_dirs):
                continue
            data = _read_agent_file(work_dir, rel)
            if data is None:
                continue
            total += len(data)
            if (len(data) > _NEW_FILE_MAX_BYTES or total > _NEW_FILE_MAX_TOTAL
                    or len(found) >= _NEW_FILE_MAX_COUNT):
                return {}
            found[rel] = data
    return found


def _graded_files(snapshot: dict[str, bytes], work_dir: str | None) -> dict[str, bytes]:
    """The file set the hard check runs against.

    Start from the pristine snapshot. With a work_dir, replace each
    overlay-eligible fixture file with the agent's version (dropping it if the
    agent deleted it), and add the new source files `_new_file_eligible`
    admits. Tests and pytest/interpreter config are only ever the fixture's."""
    files = dict(snapshot)
    if work_dir is None:
        return files
    for rel in snapshot:
        if not _overlay_eligible(rel):
            continue
        agent = _read_agent_file(work_dir, rel)
        if agent is None:
            files.pop(rel, None)
        else:
            files[rel] = agent
    files.update(_new_agent_files(snapshot, work_dir))
    return files


def _materialize(files: dict[str, bytes], dest: str) -> None:
    for rel, data in files.items():
        path = os.path.join(dest, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)


def _fresh_grade_dir(files: dict[str, bytes]) -> str:
    grade_dir = tempfile.mkdtemp(prefix="skillopt-grade-")
    _materialize(files, grade_dir)
    return grade_dir


def _source_texts(files: dict[str, bytes]) -> dict[str, str]:
    """Non-test .py sources decoded for the judge-facing diff."""
    return {
        rel: data.decode("utf-8", errors="replace")
        for rel, data in files.items()
        if rel.endswith(".py") and not _is_test_path(rel)
    }


def _diff_sources(pre: dict[str, str], post: dict[str, str]) -> str:
    """Unified diff of the graded source files against the pristine fixture."""
    chunks: list[str] = []
    for b in sorted(set(pre) | set(post)):
        before, after = pre.get(b, ""), post.get(b, "")
        if before == after:
            continue
        chunks.extend(difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"a/{b}", tofile=f"b/{b}", lineterm="",
        ))
    return "\n".join(chunks)


def _ensure_unsandboxed() -> None:
    """Claude Code's Bash sandbox (bubblewrap on Linux) overlays an isolated,
    effectively-empty view over the workspace -- the agent then sees no fixture
    files and gives up. We already isolate each rollout in a disposable work_dir,
    so tell Claude Code it's already sandboxed and should run the agent directly
    in the workspace. Respects an explicit user override.

    Also drop the coordinator/project-root hints: when skillopt is launched
    nested inside another Claude Code session, the target agents would otherwise
    inherit the PARENT session's project root and resolve their Bash tool there
    (the nearest .git ancestor = the host repo), escaping the out-of-repo
    work_dir and reaching repo files. Unsetting these makes each nested agent's
    Bash root its own disposable workspace. (Absolute-path access is still
    possible; untrusted targets still need OS-level sandboxing.)
    """
    os.environ.setdefault("CLAUDE_CODE_SANDBOXED", "1")
    for _var in ("CLAUDE_CODE_COORDINATOR_MODE", "CLAUDE_PROJECT_DIR",
                 "CLAUDE_CODE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT"):
        os.environ.pop(_var, None)


def optimizer_complete(system: str, user: str) -> str:
    """Judge/edit model call. Reuses SkillOpt's configured optimizer backend
    (claude_chat in our config). Returns raw text."""
    text, _meta = chat_optimizer(
        system=system, user=user, max_completion_tokens=4000, retries=3, stage="judge"
    )
    return text


def _build_task_text(item: dict) -> str:
    return (
        f"{item.get('task_header', '# Bug report')}\n\n"
        f"{item.get('question', '')}\n\n"
        "## Context (repo state at task start)\n\n"
        f"{item.get('context', '')}\n"
    )


# Default framing is debugging (the original target). Non-debugging fixtures
# (simplify, verify, review) override via the item's `prompt` so the agent is
# told to do the right kind of work -- a code-review fixture must NOT be told to
# "fix the bug and emit a Debug Report".
_DEFAULT_PROMPT = (
    "There is a bug in this workspace. Reproduce it, identify the root cause, "
    "then fix it so the test suite passes.\n"
    "Follow the debugging methodology in the skill exactly: build a reproduction "
    "first, confirm the test is RED before changing code, find the root cause with "
    "a file:line reference, change one thing at a time, then confirm the test is "
    "GREEN after your fix.\n"
    "When finished, emit the Debug Report (SYMPTOM / ROOT CAUSE / FIX / EVIDENCE / "
    "REGRESSION / STATUS) as your final message."
)


def _build_prompt(item: dict) -> str:
    return item.get("prompt") or _DEFAULT_PROMPT


def _eval_detail(ev: dict) -> str:
    lines = [
        "[EVALUATION RESULT]",
        f"hard (test passes) = {ev['hard']}",
        f"soft (process rubric) = {ev['soft']:.4f}",
        "per-criterion:",
    ]
    for name, c in ev.get("criteria", {}).items():
        ev_q = (c.get("evidence") or "").replace("\n", " ")[:160]
        lines.append(f"  - {name}: {c.get('score', 0.0):.2f}  evidence: {ev_q!r}")
    if ev.get("fail_reason"):
        lines.append(f"fail_reason: {ev['fail_reason']}")
    if ev.get("soft_gates_failed"):
        lines.append(f"soft before gates = {ev['soft_uncapped']:.4f}")
    return "\n".join(lines)


def process_one(
    item: dict,
    out_root: str,
    skill_content: str,
    rubric: Rubric,
    *,
    model: str = "",
    complete: Callable[[str, str], str] = optimizer_complete,
    exec_timeout: int = 300,
    test_timeout: int = 120,
    soft_gates: SoftGates | None = None,
) -> dict:
    """Run + score one fixture task."""
    gates = validate_soft_gates(rubric, soft_gates)
    _ensure_unsandboxed()
    item_id = str(item["id"])
    pred_dir = os.path.join(out_root, "predictions", item_id)
    os.makedirs(pred_dir, exist_ok=True)

    # SAFETY: run the agent in a workspace OUTSIDE the repo. Claude Code's Bash
    # tool operates at the nearest .git ancestor, so a work_dir INSIDE the repo
    # hands the bypassPermissions agent (its own sandbox disabled via
    # CLAUDE_CODE_SANDBOXED, see _ensure_unsandboxed) write access to the whole
    # repo -- a target model has run repo-relative `rm -rf` and deleted source
    # files. A tmpdir with no .git ancestor confines relative-path operations to
    # the disposable workspace. (Absolute-path access is still possible; fully
    # untrusted use needs OS-level sandboxing -- run from a bare terminal, not
    # nested inside another Claude Code session.)
    work_root = tempfile.mkdtemp(prefix=f"skillopt-{item_id}-")
    work_dir = os.path.join(work_root, "work")

    result: dict = {
        "id": item_id,
        "question": item.get("question", ""),
        "task_description": item.get("question", ""),
        "task_type": "debugging",
        "hard": 0,
        "soft": 0.0,
        "soft_uncapped": 0.0,
        "soft_gates_failed": [],
        "criteria": {},
        "fail_reason": "",
        "response": "",
        "agent_ok": False,
        "n_turns": 0,
        "infra_error": False,
        "target_system_prompt": "",
        "target_user_prompt": "",
        "integrity_error": False,
    }
    grade_dirs: list[str] = []

    try:
        skill_md = render_skill_md(
            skill_content,
            description=item.get("skill_description", "Whetstone debugging skill under optimization."),
            preamble=item.get("preamble", "Apply this debugging methodology to fix the bug in this workspace."),
        )
        task_text = _build_task_text(item)
        prepare_workspace(work_dir=work_dir, skill_md=skill_md, task_text=task_text)

        # The pristine oracle is this in-memory snapshot, read BEFORE the agent
        # launches. The host fixture is only re-read afterwards to detect
        # tampering; grading never trusts it (or the agent's workspace) again.
        snapshot = _snapshot_fixture(item["_fixture_dir"])
        digest = _tree_digest(snapshot)
        _pin_fixture(item["_fixture_dir"], digest)

        # Fixture (buggy source + failing test) goes in AFTER prepare_workspace,
        # which rmtree's work_dir, and lands alongside task.md.
        _materialize(snapshot, work_dir)

        # Harness-trusted baseline captured BEFORE the agent runs, in its own
        # fresh copy of the snapshot: the real red test output feeds the judge
        # evidence the agent cannot fabricate.
        pre_dir = _fresh_grade_dir(snapshot)
        grade_dirs.append(pre_dir)
        _, pre_test_output, _ = run_hard(pre_dir, item.get("test_cmd"), timeout=test_timeout)

        prompt = _build_prompt(item)
        response, raw = run_target_exec(
            work_dir=work_dir,
            prompt=prompt,
            model=model,
            timeout=exec_timeout,
            allowed_tools="Read,Edit,Write,Bash",
            permission_mode="bypassPermissions",
            allow_file_edits=True,
        )
        result["agent_ok"] = bool(response or raw)
        result["response"] = response
        # --output-format text exposes no turn count; 0 means "not captured"
        # (real per-turn tracking would require --output-format stream-json).
        result["n_turns"] = 0

        try:
            post_digest = _tree_digest(_snapshot_fixture(item["_fixture_dir"]))
        except (OSError, ValueError) as e:
            post_digest = f"unreadable: {e}"
        if post_digest != digest:
            # The target reached the host fixture (absolute paths are not
            # sandboxed). Fail the rollout rather than grade it.
            result["hard"] = 0
            result["integrity_error"] = True
            result["fail_reason"] = (
                f"integrity: original fixture {item['_fixture_dir']} was modified during "
                f"the rollout (sha256 {digest[:12]} -> {post_digest[:24]}); not graded"
            )
            print(f"    [rollout] INTEGRITY FAILURE id={item_id}: {result['fail_reason']}", flush=True)
            with open(os.path.join(pred_dir, "integrity_error.txt"), "w", encoding="utf-8") as f:
                f.write(result["fail_reason"] + "\n")
            return result

        # Grade in a FRESH directory built from the snapshot, overlaying only
        # the agent's edits to non-test fixture files plus new non-test sources
        # that cannot be loaded implicitly. Tests, conftest.py, and
        # pytest/interpreter config are never carried over, so the agent cannot
        # weaken or bypass the oracle from outside the code under test.
        graded = _graded_files(snapshot, work_dir)
        grade_dir = _fresh_grade_dir(graded)
        grade_dirs.append(grade_dir)

        agent_diff = _diff_sources(_source_texts(snapshot), _source_texts(graded))
        ev = evaluate(
            grade_dir, item, response, rubric, complete,
            test_timeout=test_timeout,
            pre_test_output=pre_test_output, agent_diff=agent_diff,
            soft_gates=gates,
        )
        result["hard"] = ev["hard"]
        result["soft"] = ev["soft"]
        result["soft_uncapped"] = ev["soft_uncapped"]
        result["soft_gates_failed"] = ev["soft_gates_failed"]
        result["criteria"] = ev["criteria"]
        result["fail_reason"] = ev["fail_reason"]
        result["infra_error"] = ev["infra_error"]

        user_prompt_text = task_text + "\n\n" + prompt
        result["target_system_prompt"] = skill_md
        result["target_user_prompt"] = user_prompt_text

        conversation = [
            {"role": "system", "content": "Debugging methodology provided to the agent (workspace SKILL.md)."},
            {"role": "user", "content": user_prompt_text},
            {"role": "assistant", "content": response or "(no final message)"},
            {"role": "system", "content": _eval_detail(ev)},
        ]
        with open(os.path.join(pred_dir, "target_system_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(skill_md)
        with open(os.path.join(pred_dir, "target_user_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(user_prompt_text)
        with open(os.path.join(pred_dir, "conversation.json"), "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)

    except FixtureIntegrityError as e:
        result["fail_reason"] = f"integrity: {e}"
        result["infra_error"] = True
        result["integrity_error"] = True
        with open(os.path.join(pred_dir, "error.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    except Exception as e:  # noqa: BLE001
        # A harness exception is an infra failure, not a graded "bug unfixed".
        result["fail_reason"] = f"error: {e}"
        result["infra_error"] = True
        with open(os.path.join(pred_dir, "error.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    finally:
        # Salvage the out-of-repo scratch into the (in-repo) pred_dir for
        # inspection -- the raw transcript artifacts _persist_claude_artifacts
        # wrote next to work_dir, plus a snapshot of the agent's final workspace
        # -- then drop the tmpdir.
        # Links are copied as links, never dereferenced, so a link the agent
        # planted cannot pull a host file into pred_dir.
        try:
            for name in os.listdir(work_root):
                src = os.path.join(work_root, name)
                if os.path.isfile(src) and not os.path.islink(src):
                    shutil.copy2(src, os.path.join(pred_dir, name))
            if os.path.isdir(work_dir) and not os.path.islink(work_dir):
                snap = os.path.join(pred_dir, "work")
                if os.path.exists(snap):
                    shutil.rmtree(snap, ignore_errors=True)
                shutil.copytree(work_dir, snap, ignore=_COPY_IGNORE, symlinks=True)
        except OSError:
            pass
        shutil.rmtree(work_root, ignore_errors=True)
        for d in grade_dirs:
            shutil.rmtree(d, ignore_errors=True)

    return result


def run_batch(
    items: list[dict],
    out_root: str,
    skill_content: str,
    rubric: Rubric,
    *,
    model: str = "",
    complete: Callable[[str, str], str] = optimizer_complete,
    exec_timeout: int = 300,
    test_timeout: int = 120,
    workers: int = 4,
    soft_gates: SoftGates | None = None,
) -> list[dict]:
    """Run all items in parallel. Resume-aware via results.jsonl."""
    gates = validate_soft_gates(rubric, soft_gates)
    if not is_target_exec_backend():
        raise RuntimeError(
            "whetstone rollout requires an exec target backend (claude_code_exec). "
            "Set model.backend=claude_code_exec (or target_backend=claude_code_exec) in the config."
        )

    os.makedirs(out_root, exist_ok=True)
    results_path = os.path.join(out_root, "results.jsonl")

    # Resume is keyed on (id, skill_hash): a cached result scored against a
    # DIFFERENT skill revision is stale and must be re-run, or the gate would
    # compare rewards computed against two different skills.
    skill_hash = hashlib.sha1(skill_content.encode("utf-8")).hexdigest()[:12]
    policy_hash = ""
    if gates:
        policy = json.dumps({"rubric": rubric, "soft_gates": gates}, sort_keys=True)
        policy_hash = hashlib.sha256(policy.encode("utf-8")).hexdigest()

    done_ids: set[str] = set()
    existing: list[dict] = []
    if os.path.exists(results_path):
        with open(results_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("skill_hash") != skill_hash:
                    continue  # stale: scored against another skill revision
                if r.get("soft_gates_hash", "") != policy_hash:
                    continue
                done_ids.add(str(r["id"]))
                existing.append(r)

    pending = [it for it in items if str(it["id"]) not in done_ids]
    if not pending:
        return existing

    total = len(existing) + len(pending)
    completed = len(existing)
    hard_count = sum(1 for r in existing if r.get("hard"))
    results = list(existing)

    def _run_one(item: dict) -> dict:
        return process_one(
            item, out_root, skill_content, rubric,
            model=model, complete=complete,
            exec_timeout=exec_timeout, test_timeout=test_timeout,
            soft_gates=gates,
        )

    with open(results_path, "a") as outf:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = {ex.submit(_run_one, it): it for it in pending}
            pending_futs = set(futs)
            while pending_futs:
                done, _ = wait(pending_futs, timeout=10, return_when=FIRST_COMPLETED)
                for fut in done:
                    pending_futs.remove(fut)
                    item = futs[fut]
                    try:
                        res = fut.result()
                    except Exception as exc:  # noqa: BLE001
                        res = {
                            "id": str(item["id"]), "hard": 0, "soft": 0.0, "criteria": {},
                            "fail_reason": f"unexpected: {type(exc).__name__}: {exc}",
                            "task_type": "debugging", "agent_ok": False, "n_turns": 0,
                            "infra_error": True,
                        }
                    res["skill_hash"] = skill_hash
                    res["soft_gates_hash"] = policy_hash
                    results.append(res)
                    completed += 1
                    if res.get("hard"):
                        hard_count += 1
                    acc = hard_count / completed if completed else 0.0
                    print(
                        f"    [rollout] {completed}/{total} (hard_acc={acc:.3f}) "
                        f"id={res['id']} hard={res.get('hard', '?')} soft={res.get('soft', 0.0):.3f}",
                        flush=True,
                    )
                    outf.write(json.dumps(res, ensure_ascii=False) + "\n")
                    outf.flush()

    return results
