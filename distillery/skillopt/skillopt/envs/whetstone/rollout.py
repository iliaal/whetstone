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
import glob
import hashlib
import json
import os
import shutil
import tempfile
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable

from skillopt.model import chat_optimizer, is_target_exec_backend
from skillopt.model.codex_harness import prepare_workspace, render_skill_md, run_target_exec

from .evaluator import evaluate, run_hard
from .rubric import Rubric

_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git")


def _snapshot_sources(fixture_dir: str) -> dict[str, str]:
    """Read the pristine (buggy) source files from a fixture, excluding tests.
    Used to compute a harness-trusted diff of what the agent actually changed."""
    out: dict[str, str] = {}
    for p in glob.glob(os.path.join(fixture_dir, "*.py")):
        b = os.path.basename(p)
        if b.startswith("test_"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                out[b] = f.read()
        except OSError:
            pass
    return out


def _diff_sources(pre: dict[str, str], work_dir: str) -> str:
    """Unified diff of the agent's source edits (pre-rollout vs post-rollout)."""
    chunks: list[str] = []
    for b, before in sorted(pre.items()):
        after = ""
        ap = os.path.join(work_dir, b)
        if os.path.exists(ap):
            try:
                with open(ap, encoding="utf-8") as f:
                    after = f.read()
            except OSError:
                pass
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
    """
    os.environ.setdefault("CLAUDE_CODE_SANDBOXED", "1")


def optimizer_complete(system: str, user: str) -> str:
    """Judge/edit model call. Reuses SkillOpt's configured optimizer backend
    (claude_chat in our config). Returns raw text."""
    text, _meta = chat_optimizer(
        system=system, user=user, max_completion_tokens=4000, retries=3, stage="judge"
    )
    return text


def _build_task_text(item: dict) -> str:
    return (
        "# Bug report\n\n"
        f"{item.get('question', '')}\n\n"
        "## Context (repo state at task start)\n\n"
        f"{item.get('context', '')}\n"
    )


def _build_prompt(item: dict) -> str:
    return (
        "There is a bug in this workspace. Reproduce it, identify the root cause, "
        "then fix it so the test suite passes.\n"
        "Follow the debugging methodology in the skill exactly: build a reproduction "
        "first, confirm the test is RED before changing code, find the root cause with "
        "a file:line reference, change one thing at a time, then confirm the test is "
        "GREEN after your fix.\n"
        "When finished, emit the Debug Report (SYMPTOM / ROOT CAUSE / FIX / EVIDENCE / "
        "REGRESSION / STATUS) as your final message."
    )


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
) -> dict:
    """Run + score one fixture task."""
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
        "criteria": {},
        "fail_reason": "",
        "response": "",
        "agent_ok": False,
        "n_turns": 0,
        "infra_error": False,
        "target_system_prompt": "",
        "target_user_prompt": "",
    }

    try:
        skill_md = render_skill_md(
            skill_content,
            description="Whetstone debugging skill under optimization.",
            preamble="Apply this debugging methodology to fix the bug in this workspace.",
        )
        task_text = _build_task_text(item)
        prepare_workspace(work_dir=work_dir, skill_md=skill_md, task_text=task_text)

        # Fixture (buggy source + failing test) goes in AFTER prepare_workspace,
        # which rmtree's work_dir. dirs_exist_ok lets it land alongside task.md.
        # symlinks=True so a link inside a fixture is recreated as a link (and
        # breaks harmlessly) rather than dereferenced into a host-file copy.
        shutil.copytree(
            item["_fixture_dir"], work_dir,
            dirs_exist_ok=True, ignore=_COPY_IGNORE, symlinks=True,
        )

        # Harness-trusted baselines captured BEFORE the agent runs: the real
        # red test output and a snapshot of the buggy source for the diff. These
        # feed the judge evidence the agent cannot fabricate.
        _, pre_test_output, _ = run_hard(work_dir, item.get("test_cmd"), timeout=test_timeout)
        pre_sources = _snapshot_sources(item["_fixture_dir"])

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

        # Integrity: grade `hard` against the PRISTINE fixture test, not the
        # agent's copy. The agent could otherwise pass by weakening the test.
        for tf in glob.glob(os.path.join(item["_fixture_dir"], "test_*.py")):
            shutil.copy2(tf, os.path.join(work_dir, os.path.basename(tf)))

        agent_diff = _diff_sources(pre_sources, work_dir)
        ev = evaluate(
            work_dir, item, response, rubric, complete,
            test_timeout=test_timeout,
            pre_test_output=pre_test_output, agent_diff=agent_diff,
        )
        result["hard"] = ev["hard"]
        result["soft"] = ev["soft"]
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
        try:
            for name in os.listdir(work_root):
                src = os.path.join(work_root, name)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(pred_dir, name))
            if os.path.isdir(work_dir):
                snap = os.path.join(pred_dir, "work")
                if os.path.exists(snap):
                    shutil.rmtree(snap, ignore_errors=True)
                shutil.copytree(work_dir, snap, ignore=_COPY_IGNORE)
        except OSError:
            pass
        shutil.rmtree(work_root, ignore_errors=True)

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
) -> list[dict]:
    """Run all items in parallel. Resume-aware via results.jsonl."""
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
