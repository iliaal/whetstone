#!/usr/bin/env python3
"""Materialize the HARD ia-debugging fixture task set.

Same shape as fixtures/debugging/ but the bugs are calibrated to be hard enough
that a strong baseline model does NOT fix all of them -- so baseline `hard` < 1.0
and the validation gate has room to accept a skill edit. Each fixture has
multiple tests (constraint coupling) where the obvious/naive fix fails a sibling
test or an edge case, so careful reproduction + root-cause analysis is required.

    python fixtures/debugging-hard/build_fixtures.py            # materialize
    python fixtures/debugging-hard/build_fixtures.py --verify   # check red/green

`fix_code` is the reference correct fix, used only by --verify; it is never
written into the file the agent sees.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")
SPLITS = os.path.join(HERE, "splits")
TEST_CMD = ["-m", "pytest", "-q"]


FIXTURES: list[dict] = [
    {
        "id": "hard-snapshot",
        "module": "config_store.py",
        "bug_class": "shallow vs deep copy (aliasing)",
        "fix_note": "snapshot() returns the live dict; a shallow copy fixes top-level isolation but shares nested dicts. Needs copy.deepcopy.",
        "report": (
            "Config.snapshot() must return an isolated copy of the config: mutating the "
            "returned snapshot (including nested values) must not change the live config, "
            "while Config.update() must still be reflected in later snapshots. Right now "
            "mutating a snapshot corrupts the live config."
        ),
        "code": '''import copy


class Config:
    """Holds config data. snapshot() must return a fully isolated copy."""

    def __init__(self, data):
        self._data = data

    def snapshot(self):
        return self._data

    def update(self, key, value):
        self._data[key] = value
''',
        "fix_code": '''import copy


class Config:
    """Holds config data. snapshot() must return a fully isolated copy."""

    def __init__(self, data):
        self._data = data

    def snapshot(self):
        return copy.deepcopy(self._data)

    def update(self, key, value):
        self._data[key] = value
''',
        "test": '''from config_store import Config


def _cfg():
    return Config({"name": "svc", "limits": {"cpu": 2, "mem": 512}})


def test_snapshot_toplevel_isolated():
    c = _cfg()
    snap = c.snapshot()
    snap["name"] = "HACKED"
    assert c.snapshot()["name"] == "svc"


def test_update_is_reflected():
    c = _cfg()
    c.update("name", "svc2")
    assert c.snapshot()["name"] == "svc2"


def test_snapshot_nested_isolated():
    c = _cfg()
    snap = c.snapshot()
    snap["limits"]["cpu"] = 999
    assert c.snapshot()["limits"]["cpu"] == 2
''',
    },
    {
        "id": "hard-billsplit",
        "module": "billing.py",
        "bug_class": "integer remainder distribution",
        "fix_note": "floor division drops the remainder; distribute the leftover cents to the FIRST `remainder` shares (larger shares first).",
        "report": (
            "split_bill(total_cents, n) must split a bill among n people so the shares sum "
            "EXACTLY to total_cents, differ by at most one cent, and the larger shares come "
            "first. It currently loses cents (the shares do not sum to the total)."
        ),
        "code": '''def split_bill(total_cents, n):
    """Split total_cents among n people, largest shares first, summing exactly."""
    share = total_cents // n
    return [share] * n
''',
        "fix_code": '''def split_bill(total_cents, n):
    """Split total_cents among n people, largest shares first, summing exactly."""
    share, remainder = divmod(total_cents, n)
    return [share + 1 if i < remainder else share for i in range(n)]
''',
        "test": '''from billing import split_bill


def test_sum_is_exact():
    assert sum(split_bill(1000, 3)) == 1000


def test_shares_differ_by_at_most_one():
    shares = split_bill(1000, 3)
    assert max(shares) - min(shares) <= 1


def test_larger_shares_first():
    assert split_bill(1000, 3) == [334, 333, 333]


def test_even_split():
    assert split_bill(1000, 4) == [250, 250, 250, 250]
''',
    },
    {
        "id": "hard-lru",
        "module": "lru_cache.py",
        "bug_class": "LRU recency not refreshed on read",
        "fix_note": "get() must move the key to most-recently-used; otherwise a recently-read key is wrongly evicted.",
        "report": (
            "LRUCache is a fixed-capacity cache. A get() must count as a use so the key "
            "is not the next one evicted; put() of a new key when full evicts the "
            "least-recently-used key. Right now reading a key does not protect it from "
            "eviction."
        ),
        "code": '''class LRUCache:
    """Fixed-capacity LRU cache. Insertion order in _store tracks recency."""

    def __init__(self, capacity):
        self.capacity = capacity
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def put(self, key, value):
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.capacity:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value
''',
        "fix_code": '''class LRUCache:
    """Fixed-capacity LRU cache. Insertion order in _store tracks recency."""

    def __init__(self, capacity):
        self.capacity = capacity
        self._store = {}

    def get(self, key):
        if key not in self._store:
            return None
        value = self._store.pop(key)
        self._store[key] = value
        return value

    def put(self, key, value):
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.capacity:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value
''',
        "test": '''from lru_cache import LRUCache


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")            # 'a' is now most-recently-used
    c.put("c", 3)         # should evict 'b', not 'a'
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_update_existing_value():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("a", 10)
    assert c.get("a") == 10
''',
    },
    {
        "id": "hard-merge",
        "module": "merge_streams.py",
        "bug_class": "unstable tie-break on sort",
        "fix_note": "sorted(merged) breaks ties by label; sort by timestamp only and rely on the stable sort to keep stream/append order.",
        "report": (
            "merge(*streams) merges event streams (each a list of (timestamp, label) already "
            "sorted by timestamp) into one timestamp-ordered list. On equal timestamps, events "
            "from an earlier stream argument must come before events from a later one, and "
            "original order within a stream is kept. Ties are currently ordered wrongly."
        ),
        "code": '''def merge(*streams):
    """Merge timestamp-sorted (timestamp, label) streams into one ordered list."""
    merged = []
    for stream in streams:
        merged.extend(stream)
    return sorted(merged)
''',
        "fix_code": '''def merge(*streams):
    """Merge timestamp-sorted (timestamp, label) streams into one ordered list."""
    merged = []
    for stream in streams:
        merged.extend(stream)
    return sorted(merged, key=lambda event: event[0])
''',
        "test": '''from merge_streams import merge


def test_orders_by_timestamp():
    assert merge([(1, "a"), (3, "c")], [(2, "b")]) == [(1, "a"), (2, "b"), (3, "c")]


def test_tie_preserves_stream_order():
    # stream 0 has 'b' at ts 1, stream 1 has 'a' at ts 1; stream 0 must come first
    assert merge([(1, "b")], [(1, "a")]) == [(1, "b"), (1, "a")]


def test_tie_keeps_within_stream_order():
    assert merge([(1, "x"), (1, "y")], []) == [(1, "x"), (1, "y")]
''',
    },
    {
        "id": "hard-parse",
        "module": "money_report.py",
        "bug_class": "misdirected root cause (error surfaces in caller)",
        "fix_note": "ValueError raised inside format_total's sum(), but the root cause is parse_amount not stripping the thousands comma. Fix parse_amount, not format_total.",
        "report": (
            "format_total(amounts) sums currency strings like '$1,234.50' and returns the "
            "total as a '$<amount>' string. It raises a ValueError on any amount that uses a "
            "thousands separator. The traceback points inside format_total, but the total "
            "must come out correct."
        ),
        "code": '''def parse_amount(text):
    """Parse a currency string like '$1,234.50' into integer cents."""
    cleaned = text.replace("$", "")
    return round(float(cleaned) * 100)


def format_total(amounts):
    """Sum currency strings and return the total formatted as '$<amount>'."""
    total_cents = sum(parse_amount(a) for a in amounts)
    return f"${total_cents / 100:.2f}"
''',
        "fix_code": '''def parse_amount(text):
    """Parse a currency string like '$1,234.50' into integer cents."""
    cleaned = text.replace("$", "").replace(",", "")
    return round(float(cleaned) * 100)


def format_total(amounts):
    """Sum currency strings and return the total formatted as '$<amount>'."""
    total_cents = sum(parse_amount(a) for a in amounts)
    return f"${total_cents / 100:.2f}"
''',
        "test": '''from money_report import format_total


def test_simple_total():
    assert format_total(["$25.00", "$5.50"]) == "$30.50"


def test_thousands_separator():
    assert format_total(["$1,000.50", "$25.00"]) == "$1025.50"


def test_empty_is_zero():
    assert format_total([]) == "$0.00"
''',
    },
    {
        "id": "hard-mutdefault",
        "module": "accumulate.py",
        "bug_class": "mutable default argument shared across calls",
        "fix_note": "default [] is created once and shared; use a None sentinel. A naive 'bucket=[] inside' breaks the explicit-bucket accumulate case.",
        "report": (
            "collect(item, bucket=None) appends item to bucket and returns it. A call with no "
            "explicit bucket must start from an EMPTY list, but an explicit bucket passed in "
            "must accumulate across calls. Right now independent calls leak state into each "
            "other."
        ),
        "code": '''def collect(item, bucket=[]):
    """Append item to bucket and return it; no-bucket calls start empty."""
    bucket.append(item)
    return bucket
''',
        "fix_code": '''def collect(item, bucket=None):
    """Append item to bucket and return it; no-bucket calls start empty."""
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
''',
        "test": '''from accumulate import collect


def test_independent_calls_start_empty():
    assert collect(1) == [1]
    assert collect(2) == [2]


def test_explicit_bucket_accumulates():
    b = []
    collect(1, b)
    collect(2, b)
    assert b == [1, 2]
''',
    },
    {
        "id": "hard-pagination",
        "module": "pages.py",
        "bug_class": "integer floor division drops the partial last page",
        "fix_note": "floor division loses the remainder page; ceil division is (total + per - 1) // per. A naive 'total // per + 1' over-counts exact multiples and empty input.",
        "report": (
            "page_count(total, per_page) returns how many pages are needed to show `total` "
            "items at `per_page` each. It currently drops the final partial page (101 items at "
            "10/page must be 11 pages, not 10), while exact multiples and zero items must still "
            "be right."
        ),
        "code": '''def page_count(total, per_page):
    """Pages needed to show `total` items at `per_page` each."""
    return total // per_page
''',
        "fix_code": '''def page_count(total, per_page):
    """Pages needed to show `total` items at `per_page` each."""
    return (total + per_page - 1) // per_page
''',
        "test": '''from pages import page_count


def test_exact_multiple():
    assert page_count(100, 10) == 10


def test_partial_last_page():
    assert page_count(101, 10) == 11


def test_fewer_than_one_page():
    assert page_count(5, 10) == 1


def test_zero_items():
    assert page_count(0, 10) == 0
''',
    },
    {
        "id": "hard-floatcents",
        "module": "money.py",
        "bug_class": "float truncation vs rounding",
        "fix_note": "int() truncates the binary-float error (0.29 -> 28.9999... -> int 28); round() gives 29. A naive per-element int(p*100) also truncates and fails the same case.",
        "report": (
            "total_cents(prices) sums a list of dollar amounts (floats) and returns whole "
            "cents. It loses a cent on amounts that aren't exactly representable in binary "
            "float ([0.29] must be 29 cents, not 28), while exact amounts stay correct."
        ),
        "code": '''def total_cents(prices):
    """Sum dollar floats and return whole cents."""
    return int(sum(prices) * 100)
''',
        "fix_code": '''def total_cents(prices):
    """Sum dollar floats and return whole cents."""
    return round(sum(prices) * 100)
''',
        "test": '''from money import total_cents


def test_truncation_drops_a_cent():
    assert total_cents([0.29]) == 29


def test_accumulated_truncation():
    assert total_cents([0.29, 0.29]) == 58


def test_exact():
    assert total_cents([1.0, 2.0]) == 300
''',
    },
    {
        "id": "hard-stripchars",
        "module": "prefix.py",
        "bug_class": "str.lstrip strips a character SET, not a prefix",
        "fix_note": "lstrip(prefix) removes any leading chars in the set, not the literal prefix; use startswith + slice (or removeprefix). A naive replace(prefix, '', 1) removes the first OCCURRENCE anywhere, not only a leading one.",
        "report": (
            "remove_prefix(s, prefix) must remove `prefix` from the start of s exactly once, "
            "and leave s unchanged when it does not start with prefix. It currently strips too "
            "much: remove_prefix('foofoobar', 'fo') must be 'ofoobar', and remove_prefix('ooze', "
            "'fo') must be 'ooze' (the 'o' is in the prefix charset but 'ooze' has no 'fo' "
            "prefix)."
        ),
        "code": '''def remove_prefix(s, prefix):
    """Remove a leading `prefix` once; unchanged if absent."""
    return s.lstrip(prefix)
''',
        "fix_code": '''def remove_prefix(s, prefix):
    """Remove a leading `prefix` once; unchanged if absent."""
    return s[len(prefix):] if s.startswith(prefix) else s
''',
        "test": '''from prefix import remove_prefix


def test_removes_prefix():
    assert remove_prefix("foobar", "foo") == "bar"


def test_absent_prefix_unchanged():
    assert remove_prefix("bazbar", "foo") == "bazbar"


def test_strips_one_prefix_not_charset():
    assert remove_prefix("foofoobar", "fo") == "ofoobar"


def test_charset_member_not_prefix_unchanged():
    assert remove_prefix("ooze", "fo") == "ooze"
''',
    },
    {
        "id": "hard-inplace",
        "module": "ranking.py",
        "bug_class": "in-place mutation of a caller's argument",
        "fix_note": "list.sort() mutates the caller's list; sorted() returns a new list. A naive 'c = items; c.sort()' still aliases and mutates; need sorted() or items.copy().",
        "report": (
            "top_n(items, n) returns the n largest items in descending order and must NOT "
            "mutate its input list. It currently sorts the caller's list in place, so the "
            "caller's data is reordered as a side effect."
        ),
        "code": '''def top_n(items, n):
    """The n largest items, descending; must not mutate the input."""
    items.sort(reverse=True)
    return items[:n]
''',
        "fix_code": '''def top_n(items, n):
    """The n largest items, descending; must not mutate the input."""
    return sorted(items, reverse=True)[:n]
''',
        "test": '''from ranking import top_n


def test_returns_top_n():
    assert top_n([3, 1, 4, 1, 5], 2) == [5, 4]


def test_does_not_mutate_input():
    data = [3, 1, 4, 1, 5]
    top_n(data, 2)
    assert data == [3, 1, 4, 1, 5]
''',
    },
]

# train drives reflection; val drives the gate. Overlap is intentional here:
# this set is a mechanics demo (can the gate accept an edit?), not a clean
# generalization eval. All ten bug classes appear in both so the gate sees each.
# n_val = 10 -> the soft-blend ceiling tightens to lambda < 1/10 = 0.1.
_ALL = ["hard-snapshot", "hard-billsplit", "hard-lru", "hard-merge", "hard-parse",
        "hard-mutdefault", "hard-pagination", "hard-floatcents", "hard-stripchars", "hard-inplace"]
SPLIT_ASSIGN = {
    "train": list(_ALL),
    "val":   list(_ALL),
    "test":  ["hard-parse", "hard-stripchars"],
}


def _context(fx: dict) -> str:
    module = fx["module"]
    return (
        f"Workspace files:\n  {module}   (the module under test, contains a bug)\n"
        f"  test_{module}   (pytest; currently failing)\n\n"
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
        with open(os.path.join(split_dir, "items.json"), "w", encoding="utf-8") as f:
            json.dump([_item(by_id[i]) for i in ids], f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(FIXTURES)} hard fixtures to {TASKS}")
    print(f"Splits: {dict((s, len(ids)) for s, ids in SPLIT_ASSIGN.items())}")


def _run_pytest(code: str, test: str, module: str) -> int:
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, module), "w") as f:
            f.write(code)
        with open(os.path.join(d, f"test_{module}"), "w") as f:
            f.write(test)
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=d,
            capture_output=True, text=True,
        ).returncode


def verify() -> int:
    ok = True
    for fx in FIXTURES:
        buggy_rc = _run_pytest(fx["code"], fx["test"], fx["module"])
        fixed_rc = _run_pytest(fx["fix_code"], fx["test"], fx["module"])
        red = buggy_rc != 0
        green = fixed_rc == 0
        status = "OK" if (red and green) else "BROKEN"
        if not (red and green):
            ok = False
        print(f"  [{status}] {fx['id']:16} buggy={'RED' if red else 'GREEN(!)'} "
              f"fixed={'GREEN' if green else 'RED(!)'}")
    print("All fixtures well-formed (red-on-bug, green-on-fix)." if ok
          else "SOME FIXTURES BROKEN -- do not use until fixed.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify())
    main()
