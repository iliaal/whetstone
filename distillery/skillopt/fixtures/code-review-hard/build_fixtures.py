#!/usr/bin/env python3
"""Materialize the ia-code-review fixture task set (detection-graded).

ia-code-review REPORTS defects; it does not edit code, so pytest red->green does
not apply. Each fixture is a small module with ONE subtle planted defect. The
agent reviews it and emits findings as its final message; `evaluator.run_detection`
grades hard = did the report NAME the planted defect (localize to the function +
identify the mechanism). The ground-truth `detection` spec lives in
splits/items.json -- which is NEVER copied into the agent's workspace -- so the
agent cannot read the answer key; only a real review earns hard=1.

Defects are subtle (a careless review misses them): SQL injection by
concatenation, a TOCTOU race, a mutable default argument, an unclosed file
handle, and an off-by-one that drops the last element -- spanning the skill's
security / concurrency / correctness / reliability categories.

    python fixtures/code-review-hard/build_fixtures.py            # materialize
    python fixtures/code-review-hard/build_fixtures.py --verify   # good review -> hard=1, miss -> 0

`good_review` / `bad_review` are reference reports used only by --verify; they are
never written into the agent's workspace.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")
SPLITS = os.path.join(HERE, "splits")
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

_REVIEW_PROMPT = (
    "Review the code file in this workspace for defects -- correctness, security, "
    "concurrency, and reliability. Apply the review methodology in the skill. Do NOT "
    "modify the code.\n"
    "Produce your review as your FINAL MESSAGE: a list of findings, each naming the "
    "function and citing the file and the specific issue (the mechanism, not a vague "
    "concern), with a severity and a concrete fix. If the code is clean, say so "
    "explicitly with what you checked."
)
_PREAMBLE = "Apply this code-review methodology to the code in this workspace and report the findings."
_SKILL_DESC = "Whetstone code-review skill under optimization."


FIXTURES: list[dict] = [
    {
        "id": "cr-sqli",
        "module": "userdb.py",
        "category": "security",
        "code": '''def find_user(conn, name):
    """Look up a single user row by name."""
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    cursor.execute(query)
    return cursor.fetchone()
''',
        "detection": {
            "must_localize": ["find_user"],
            "must_include_any": ["inject", "concat", "parameter", "sanitiz", "untrusted", "prepared statement"],
        },
        "good_review": "## Review\n### Critical\n- CR-001. userdb.py:4 `find_user` builds the query by concatenating `name` into the SQL string -- this is a SQL injection. Fix: use a parameterized query, `cursor.execute(sql, (name,))`.\n### Verdict\nNot ready.",
        "bad_review": "## Review\n`find_user` opens a cursor, runs a lookup by name, and returns one row. Naming is clear and the flow is easy to follow. No issues found.\n### Verdict\nReady to merge.",
    },
    {
        "id": "cr-toctou",
        "module": "fileops.py",
        "category": "concurrency",
        "code": '''import os


def safe_write(path, data):
    """Write data to path only if the file does not already exist."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(data)
        return True
    return False
''',
        "detection": {
            "must_localize": ["safe_write"],
            "must_include_any": ["race", "toctou", "time-of-check", "time of check",
                                 "check-then-act", "check then act", "atomic", "exclusive", "o_excl", "'x'"],
        },
        "good_review": "## Review\n### Important\n- CR-001. fileops.py `safe_write` checks `os.path.exists` and then opens the file -- a TOCTOU race: another process can create the file between the check and the write. Fix: open atomically with `open(path, 'x')` (O_CREAT|O_EXCL) and catch FileExistsError.\n### Verdict\nReady with fixes.",
        "bad_review": "## Review\n`safe_write` returns False when the file exists and otherwise writes it. The context manager closes the handle correctly and the return values are clear. Looks good.\n### Verdict\nReady to merge.",
    },
    {
        "id": "cr-mutdefault",
        "module": "collector.py",
        "category": "correctness",
        "code": '''def add_tag(tag, tags=[]):
    """Append tag to tags and return the list."""
    tags.append(tag)
    return tags
''',
        "detection": {
            "must_localize": ["add_tag"],
            "must_include_any": ["mutable default", "default argument", "default list",
                                 "default mutable", "shared", "sentinel", "created once"],
        },
        "good_review": "## Review\n### Important\n- CR-001. collector.py `add_tag(tag, tags=[])` uses a mutable default argument -- the list is created once at definition and shared across all calls that omit it, so state leaks between calls. Fix: default to None and create the list inside.\n### Verdict\nReady with fixes.",
        "bad_review": "## Review\n`add_tag` appends the tag to the list and returns it -- a small, clear helper. The return value is convenient for chaining. No concerns.\n### Verdict\nReady to merge.",
    },
    {
        "id": "cr-leak",
        "module": "config.py",
        "category": "reliability",
        "code": '''def load_count(path):
    """Return the number of lines in the file at path."""
    f = open(path)
    data = f.read()
    return len(data.splitlines())
''',
        "detection": {
            "must_localize": ["load_count"],
            "must_include_any": ["leak", "not closed", "never closed", "close", "context manager",
                                 "with open", "with statement", "resource", "file handle", "file descriptor"],
        },
        "good_review": "## Review\n### Medium\n- CR-001. config.py `load_count` opens the file but never closes it -- a file-handle leak, and the handle stays open if `read()` raises. Fix: use `with open(path) as f:`.\n### Verdict\nReady with fixes.",
        "bad_review": "## Review\n`load_count` reads the file and returns the number of lines via splitlines(). Straightforward and correct for the stated purpose. No problems found.\n### Verdict\nReady to merge.",
    },
    {
        "id": "cr-offbyone",
        "module": "window.py",
        "category": "correctness",
        "code": '''def last_n(items, n):
    """Return the last n items of the list, in their original order."""
    result = []
    for i in range(len(items) - n, len(items) - 1):
        result.append(items[i])
    return result
''',
        "detection": {
            "must_localize": ["last_n"],
            "must_include_any": ["off-by-one", "off by one", "drops the last", "misses the last",
                                 "len(items) - 1", "last element", "one short", "returns n-1", "returns n - 1"],
        },
        "good_review": "## Review\n### Critical\n- CR-001. window.py `last_n` loops `range(len(items) - n, len(items) - 1)` -- the `- 1` is an off-by-one that drops the last element, so it returns n-1 items instead of n. Fix: use `range(len(items) - n, len(items))` (or `items[-n:]`).\n### Verdict\nNot ready.",
        "bad_review": "## Review\n`last_n` collects items from a computed start index to the end using a range loop and returns them in order. The indexing approach is reasonable. No problems found.\n### Verdict\nReady to merge.",
    },
]

SPLIT_ASSIGN = {
    "train": ["cr-sqli", "cr-toctou", "cr-mutdefault", "cr-leak", "cr-offbyone"],
    "val":   ["cr-sqli", "cr-toctou", "cr-mutdefault", "cr-leak", "cr-offbyone"],
    "test":  ["cr-mutdefault"],
}


def _context(fx: dict) -> str:
    return (
        f"Workspace files:\n  {fx['module']}   (under review)\n\n"
        f"Report every real defect you find, naming the function and the specific issue. "
        f"Do not edit the code -- review and report only."
    )


def _item(fx: dict) -> dict:
    return {
        "id": fx["id"],
        "question": f"Review `{fx['module']}` for defects and report your findings.",
        "context": _context(fx),
        "fixture": fx["id"],
        "prompt": _REVIEW_PROMPT,
        "preamble": _PREAMBLE,
        "task_header": "# Code review request",
        "skill_description": _SKILL_DESC,
        "detection": fx["detection"],
    }


def main() -> None:
    by_id = {fx["id"]: fx for fx in FIXTURES}
    for fx in FIXTURES:
        task_dir = os.path.join(TASKS, fx["id"])
        os.makedirs(task_dir, exist_ok=True)
        # Only the code goes in the agent's workspace -- no test file, no spec.
        with open(os.path.join(task_dir, fx["module"]), "w", encoding="utf-8") as f:
            f.write(fx["code"])
    for split, ids in SPLIT_ASSIGN.items():
        split_dir = os.path.join(SPLITS, split)
        os.makedirs(split_dir, exist_ok=True)
        with open(os.path.join(split_dir, "items.json"), "w", encoding="utf-8") as f:
            json.dump([_item(by_id[i]) for i in ids], f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(FIXTURES)} code-review fixtures to {TASKS}")
    print(f"Splits: {dict((s, len(ids)) for s, ids in SPLIT_ASSIGN.items())}")


def verify() -> int:
    from skillopt.envs.whetstone.evaluator import run_detection
    ok = True
    for fx in FIXTURES:
        spec = fx["detection"]
        good = run_detection(fx["good_review"], spec)[0] == 1
        bad = run_detection(fx["bad_review"], spec)[0] == 0
        good_ok = good and bad
        ok = ok and good_ok
        print(f"  [{'OK' if good_ok else 'BROKEN'}] {fx['id']:14} "
              f"good_review={'DETECTED' if good else 'MISSED(!)'} "
              f"bad_review={'MISSED' if bad else 'DETECTED(!)'}")
    print("All fixtures well-formed (a real review detects; a clean-bill miss does not)." if ok
          else "SOME FIXTURES BROKEN -- do not use until fixed.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify())
    main()
