#!/usr/bin/env python3
"""Materialize the ia-verification-before-completion fixture task set.

Same pytest harness as debugging-hard, but calibrated for the verification
skill's failure mode: each module is reported "implemented and complete," its
HAPPY-PATH test passes, but an ADVERSARIAL/edge test fails (boundary, empty,
idempotency, orphan id, zero/negative). A model that trusts the "done" claim or
runs a cursory check signs off with the edge test still red (hard=0); a model
that runs the FULL suite fresh -- the skill's Gate Function + Adversarial Probes
-- catches the edge, fixes it, and re-verifies green (hard=1). So hard correlates
with verification discipline, and the soft rubric scores the process directly.

Each fixture's edge case maps to one of the skill's Adversarial Probes.

    python fixtures/verification-hard/build_fixtures.py            # materialize
    python fixtures/verification-hard/build_fixtures.py --verify   # check red/green

`fix_code` is the reference fix, used only by --verify; never written into the
file the agent sees.
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
        "id": "ver-boundary",
        "module": "range_check.py",
        "probe": "boundary value (inclusive endpoints)",
        "report": (
            "in_range(x, lo, hi) was implemented and reported COMPLETE: it must return True "
            "when x is within [lo, hi] INCLUSIVE. The happy-path cases work. Before signing "
            "off, verify it is actually complete -- confirm the boundary behavior the spec "
            "requires and fix anything the full test run surfaces."
        ),
        "code": '''def in_range(x, lo, hi):
    """True when x is within [lo, hi] inclusive."""
    return lo < x < hi
''',
        "fix_code": '''def in_range(x, lo, hi):
    """True when x is within [lo, hi] inclusive."""
    return lo <= x <= hi
''',
        "test": '''from range_check import in_range


def test_inside():
    assert in_range(5, 0, 10) is True


def test_below():
    assert in_range(-1, 0, 10) is False


def test_boundary_is_inclusive():
    assert in_range(10, 0, 10) is True
    assert in_range(0, 0, 10) is True
''',
    },
    {
        "id": "ver-empty",
        "module": "agg.py",
        "probe": "empty collection",
        "report": (
            "average(nums) was implemented and reported COMPLETE: the arithmetic mean of nums, "
            "or 0 for an empty list. It works on normal input. Before signing off, verify it is "
            "actually complete against the spec and fix anything the full test run surfaces."
        ),
        "code": '''def average(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    return sum(nums) / len(nums)
''',
        "fix_code": '''def average(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    return sum(nums) / len(nums) if nums else 0
''',
        "test": '''from agg import average


def test_average():
    assert average([2, 4, 6]) == 4


def test_single():
    assert average([10]) == 10


def test_empty_is_zero():
    assert average([]) == 0
''',
    },
    {
        "id": "ver-idempotency",
        "module": "cart.py",
        "probe": "idempotency (apply twice)",
        "report": (
            "Cart.apply_discount(pct) was implemented and reported COMPLETE: it applies a "
            "percentage discount to the cart total and must be IDEMPOTENT -- applying the same "
            "discount twice must not stack. A single apply works. Before signing off, verify it "
            "is actually complete and fix anything the full test run surfaces."
        ),
        "code": '''class Cart:
    """A cart whose discount must apply at most once."""

    def __init__(self):
        self.total = 100
        self._discounted = False

    def apply_discount(self, pct):
        self.total = self.total * (1 - pct / 100)
        return self.total
''',
        "fix_code": '''class Cart:
    """A cart whose discount must apply at most once."""

    def __init__(self):
        self.total = 100
        self._discounted = False

    def apply_discount(self, pct):
        if self._discounted:
            return self.total
        self.total = self.total * (1 - pct / 100)
        self._discounted = True
        return self.total
''',
        "test": '''from cart import Cart


def test_single_discount():
    c = Cart()
    assert c.apply_discount(10) == 90


def test_idempotent_second_apply_no_ops():
    c = Cart()
    c.apply_discount(10)
    assert c.apply_discount(10) == 90
''',
    },
    {
        "id": "ver-orphan",
        "module": "store.py",
        "probe": "orphan / missing id",
        "report": (
            "get_user(users, user_id) was implemented and reported COMPLETE: return the user "
            "for user_id, or None when the id is not present. Lookups of existing users work. "
            "Before signing off, verify it is actually complete and fix anything the full test "
            "run surfaces."
        ),
        "code": '''def get_user(users, user_id):
    """Return the user for user_id, or None if absent."""
    return users[user_id]
''',
        "fix_code": '''def get_user(users, user_id):
    """Return the user for user_id, or None if absent."""
    return users.get(user_id)
''',
        "test": '''from store import get_user


def test_existing_user():
    assert get_user({"a": {"name": "Ann"}}, "a") == {"name": "Ann"}


def test_missing_id_is_none():
    assert get_user({"a": {"name": "Ann"}}, "zzz") is None
''',
    },
    {
        "id": "ver-negative",
        "module": "fee.py",
        "probe": "zero / negative boundary",
        "report": (
            "shipping_fee(weight) was implemented and reported COMPLETE: $5 base + $2 per kg, "
            "but zero or negative weight ships free (returns 0). Positive weights work. Before "
            "signing off, verify it is actually complete and fix anything the full test run "
            "surfaces."
        ),
        "code": '''def shipping_fee(weight):
    """$5 base + $2/kg; zero or negative weight ships free (0)."""
    return 5 + 2 * weight
''',
        "fix_code": '''def shipping_fee(weight):
    """$5 base + $2/kg; zero or negative weight ships free (0)."""
    if weight <= 0:
        return 0
    return 5 + 2 * weight
''',
        "test": '''from fee import shipping_fee


def test_positive_weight():
    assert shipping_fee(3) == 11


def test_zero_is_free():
    assert shipping_fee(0) == 0


def test_negative_is_free():
    assert shipping_fee(-2) == 0
''',
    },
]

SPLIT_ASSIGN = {
    "train": ["ver-boundary", "ver-empty", "ver-idempotency", "ver-orphan", "ver-negative"],
    "val":   ["ver-boundary", "ver-empty", "ver-idempotency", "ver-orphan", "ver-negative"],
    "test":  ["ver-orphan"],
}


def _context(fx: dict) -> str:
    module = fx["module"]
    return (
        f"Workspace files:\n  {module}   (reported implemented + complete; happy path works)\n"
        f"  test_{module}   (pytest; the full suite is the verification command)\n\n"
        f"Do NOT trust the 'complete' claim -- run the FULL test suite fresh and read every "
        f"result before signing off. Adversarial probe to weigh: {fx['probe']}.\n"
        f"Run `python -m pytest -q`."
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
    print(f"Wrote {len(FIXTURES)} verification fixtures to {TASKS}")
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
        buggy = _run_pytest(fx["code"], fx["test"], fx["module"]) != 0
        fixed = _run_pytest(fx["fix_code"], fx["test"], fx["module"]) == 0
        good = buggy and fixed
        ok = ok and good
        print(f"  [{'OK' if good else 'BROKEN'}] {fx['id']:16} "
              f"as-shipped={'RED' if buggy else 'GREEN(!)'} fixed={'GREEN' if fixed else 'RED(!)'}")
    print("All fixtures well-formed (red as-shipped on the edge, green when fixed)." if ok
          else "SOME FIXTURES BROKEN -- do not use until fixed.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify())
    main()
