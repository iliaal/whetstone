#!/usr/bin/env python3
"""Materialize the ia-debugging fixture task set.

Source-of-truth for the pilot fixtures. Each task is a self-contained pure-Python
module with a seeded bug and a pytest that is RED on the bug and GREEN when the
bug is correctly fixed. Re-run to regenerate tasks/ and splits/.

    python fixtures/debugging/build_fixtures.py

Each fixture covers a distinct bug class so the rubric's process criteria
(reproduce-first, root-cause-evidence, one-change-at-a-time, failing-test-first)
get real signal across the batch. The `fix_note` documents the intended root
cause for maintainers; it is NOT written into the file the agent sees.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")
SPLITS = os.path.join(HERE, "splits")

TEST_CMD = ["-m", "pytest", "-q"]


FIXTURES: list[dict] = [
    {
        "id": "dbg-001-offbyone",
        "module": "chunker.py",
        "bug_class": "off-by-one (loop bound)",
        "fix_note": "range stop drops the final partial chunk; use range(0, len(seq), size).",
        "report": (
            "chunked(seq, size) should split a list into consecutive chunks of `size`, "
            "keeping a final shorter chunk. It is dropping the last partial chunk."
        ),
        "code": '''def chunked(seq, size):
    """Split seq into consecutive chunks of length `size` (last may be shorter)."""
    out = []
    for i in range(0, len(seq) - size + 1, size):
        out.append(seq[i:i + size])
    return out
''',
        "test": '''from chunker import chunked


def test_preserves_all_elements():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_exact_multiple():
    assert chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_size_one():
    assert chunked([1, 2, 3], 1) == [[1], [2], [3]]
''',
    },
    {
        "id": "dbg-002-overlap",
        "module": "intervals.py",
        "bug_class": "wrong comparison operator (boundary)",
        "fix_note": "closed intervals overlap when a_start <= b_end and b_start <= a_end; strict < misses touching endpoints.",
        "report": (
            "overlaps(a, b) tests whether two closed integer intervals (start, end) share "
            "any point. Intervals that touch at an endpoint, like (1,5) and (5,9), are "
            "wrongly reported as non-overlapping."
        ),
        "code": '''def overlaps(a, b):
    """Return True if closed intervals a=(start,end) and b=(start,end) share a point."""
    a_start, a_end = a
    b_start, b_end = b
    return a_start < b_end and b_start < a_end
''',
        "test": '''from intervals import overlaps


def test_touching_overlaps():
    assert overlaps((1, 5), (5, 9)) is True


def test_disjoint():
    assert overlaps((1, 4), (6, 9)) is False


def test_nested():
    assert overlaps((1, 10), (3, 4)) is True
''',
    },
    {
        "id": "dbg-003-mutable-default",
        "module": "acc.py",
        "bug_class": "mutable default argument",
        "fix_note": "into=[] is shared across calls; default to None and create a fresh list.",
        "report": (
            "accumulate(value, into=None) should append value to a fresh list when no "
            "list is given. Independent calls are leaking state into each other."
        ),
        "code": '''def accumulate(value, into=[]):
    """Append value to `into` (a new list by default) and return it."""
    into.append(value)
    return into
''',
        "test": '''from acc import accumulate


def test_independent_calls():
    assert accumulate(1) == [1]
    assert accumulate(2) == [2]


def test_explicit_target():
    bucket = [0]
    assert accumulate(9, bucket) == [0, 9]
''',
    },
    {
        "id": "dbg-004-dict-mutation",
        "module": "cache_store.py",
        "bug_class": "mutate dict during iteration",
        "fix_note": "deleting while iterating store.items() raises RuntimeError; iterate over a snapshot (list(...)).",
        "report": (
            "drop_expired(store, now) should remove entries whose expiry is strictly less "
            "than now and return the store. It crashes with a RuntimeError on any removal."
        ),
        "code": '''def drop_expired(store, now):
    """Remove entries with expiry < now from the dict `store` and return it."""
    for key, expiry in store.items():
        if expiry < now:
            del store[key]
    return store
''',
        "test": '''from cache_store import drop_expired


def test_removes_expired():
    store = {"a": 1, "b": 5, "c": 2}
    assert drop_expired(store, 3) == {"b": 5}


def test_keeps_all_when_fresh():
    store = {"a": 10, "b": 11}
    assert drop_expired(store, 3) == {"a": 10, "b": 11}
''',
    },
    {
        "id": "dbg-005-error-swallow",
        "module": "pricing.py",
        "bug_class": "over-broad except swallows error",
        "fix_note": "a single missing 'price' zeroes the whole total; skip items without a price instead of catching across the whole sum.",
        "report": (
            "total_price(items) should sum the 'price' of each item, skipping items that "
            "have no 'price' key. When any item lacks a price the total comes back as 0."
        ),
        "code": '''def total_price(items):
    """Sum item['price'] across items, skipping items that have no price."""
    try:
        return sum(item["price"] for item in items)
    except KeyError:
        return 0
''',
        "test": '''from pricing import total_price


def test_skips_missing_price():
    items = [{"price": 10}, {"name": "x"}, {"price": 5}]
    assert total_price(items) == 15


def test_all_present():
    assert total_price([{"price": 2}, {"price": 3}]) == 5
''',
    },
    {
        "id": "dbg-006-stale-cache",
        "module": "configcache.py",
        "bug_class": "stale cache not invalidated",
        "fix_note": "update() mutates _data but never clears _cache, so get() returns the stale snapshot; invalidate on update.",
        "report": (
            "Config caches a snapshot of its data on first get(). After calling "
            "update(key, value), get() still returns the old value instead of the updated one."
        ),
        "code": '''class Config:
    """A config object that caches a snapshot of its data."""

    def __init__(self):
        self._data = {"level": "info"}
        self._cache = None

    def get(self):
        if self._cache is None:
            self._cache = dict(self._data)
        return self._cache

    def update(self, key, value):
        self._data[key] = value
''',
        "test": '''from configcache import Config


def test_update_is_visible():
    c = Config()
    assert c.get()["level"] == "info"
    c.update("level", "debug")
    assert c.get()["level"] == "debug"
''',
    },
    {
        "id": "dbg-007-async-ordering",
        "module": "asyncwork.py",
        "bug_class": "async: tasks never awaited",
        "fix_note": "double_all appends Task objects and returns them un-awaited; await them (or asyncio.gather) and return the results.",
        "report": (
            "double_all(values) is an async function that should return each value doubled. "
            "It returns un-awaited task objects instead of the computed results."
        ),
        "code": '''import asyncio


async def _double(x):
    await asyncio.sleep(0)
    return x * 2


async def double_all(values):
    """Return [v*2 for v in values], computed concurrently."""
    results = []
    for v in values:
        task = asyncio.create_task(_double(v))
        results.append(task)
    return results
''',
        "test": '''import asyncio

from asyncwork import double_all


def test_doubles_all():
    assert asyncio.run(double_all([1, 2, 3])) == [2, 4, 6]


def test_empty():
    assert asyncio.run(double_all([])) == []
''',
    },
    {
        "id": "dbg-008-binary-search",
        "module": "search.py",
        "bug_class": "binary search boundary (off-by-one)",
        "fix_note": "hi = mid - 1 skips the target in the lower-bound search; hi should become mid.",
        "report": (
            "index_of(sorted_seq, target) should return the index of target in a sorted "
            "list, or -1 if absent. It returns -1 for values that are present."
        ),
        "code": '''def index_of(sorted_seq, target):
    """Return the index of target in sorted_seq, or -1 if absent."""
    lo, hi = 0, len(sorted_seq)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_seq[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    if lo < len(sorted_seq) and sorted_seq[lo] == target:
        return lo
    return -1
''',
        "test": '''from search import index_of


def test_finds_middle():
    assert index_of([1, 3, 5, 7], 5) == 2


def test_finds_ends():
    assert index_of([1, 3, 5, 7], 1) == 0
    assert index_of([1, 3, 5, 7], 7) == 3


def test_absent():
    assert index_of([1, 3, 5, 7], 4) == -1
''',
    },
    {
        "id": "dbg-009-accumulator",
        "module": "stats.py",
        "bug_class": "wrong variable appended",
        "fix_note": "running_max appends x instead of the tracked maximum m.",
        "report": (
            "running_max(seq) should return the running maximum at each position. It is "
            "returning the input values unchanged instead of the running max."
        ),
        "code": '''def running_max(seq):
    """Return a list where element i is max(seq[0..i])."""
    result = []
    m = None
    for x in seq:
        m = x if m is None else max(m, x)
        result.append(x)
    return result
''',
        "test": '''from stats import running_max


def test_running_max():
    assert running_max([1, 3, 2, 5, 4]) == [1, 3, 3, 5, 5]


def test_monotone():
    assert running_max([5, 4, 3]) == [5, 5, 5]
''',
    },
    {
        "id": "dbg-010-early-return",
        "module": "predicates.py",
        "bug_class": "early return inside loop",
        "fix_note": "the loop returns on the first element; it must scan all elements before returning True.",
        "report": (
            "all_positive(seq) should return True only if every element is > 0. It returns "
            "True for lists whose first element is positive even when later ones are not."
        ),
        "code": '''def all_positive(seq):
    """Return True if every element of seq is strictly positive."""
    for x in seq:
        if x > 0:
            return True
        else:
            return False
    return True
''',
        "test": '''from predicates import all_positive


def test_has_negative():
    assert all_positive([1, 2, -3]) is False


def test_all_positive():
    assert all_positive([1, 2, 3]) is True


def test_empty_is_true():
    assert all_positive([]) is True
''',
    },
]

# train / val / test assignment (val drives the gate; test is held out)
SPLIT_ASSIGN = {
    "train": ["dbg-001-offbyone", "dbg-002-overlap", "dbg-003-mutable-default",
              "dbg-004-dict-mutation", "dbg-005-error-swallow", "dbg-006-stale-cache"],
    "val":   ["dbg-007-async-ordering", "dbg-008-binary-search"],
    "test":  ["dbg-009-accumulator", "dbg-010-early-return"],
}


def _context(fx: dict) -> str:
    module = fx["module"]
    test_file = f"test_{module}"
    return (
        f"Workspace files:\n  {module}   (the module under test, contains a bug)\n"
        f"  {test_file}   (pytest; currently failing)\n\n"
        f"Bug class: {fx['bug_class']}\n"
        f"Run `python -m pytest -q` to see the failure."
    )


def _item(fx: dict) -> dict:
    return {
        "id": fx["id"],
        "question": fx["report"],
        "context": _context(fx),
        "fixture": fx["id"],
        "test_cmd": TEST_CMD,
    }


def main() -> None:
    by_id = {fx["id"]: fx for fx in FIXTURES}

    for fx in FIXTURES:
        task_dir = os.path.join(TASKS, fx["id"])
        os.makedirs(task_dir, exist_ok=True)
        with open(os.path.join(task_dir, fx["module"]), "w", encoding="utf-8") as f:
            f.write(fx["code"])
        with open(os.path.join(task_dir, f"test_{fx['module']}"), "w", encoding="utf-8") as f:
            f.write(fx["test"])

    for split, ids in SPLIT_ASSIGN.items():
        split_dir = os.path.join(SPLITS, split)
        os.makedirs(split_dir, exist_ok=True)
        items = [_item(by_id[i]) for i in ids]
        with open(os.path.join(split_dir, "items.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    total = len(FIXTURES)
    counts = {s: len(ids) for s, ids in SPLIT_ASSIGN.items()}
    print(f"Wrote {total} fixtures to {TASKS}")
    print(f"Splits: {counts}")


if __name__ == "__main__":
    main()
