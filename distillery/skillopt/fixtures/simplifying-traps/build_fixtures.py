#!/usr/bin/env python3
"""Materialize the CALIBRATED ia-simplifying-code fixture task set.

fixtures/simplifying-hard/ saturated: haiku + the seed skill aced every
single-smell task (baseline hard=1.0, soft=0.97), leaving the gate no room. This
set adds a behavior-preservation TRAP to each fixture: the *obvious* one-liner
simplification passes the structural simplicity check but BREAKS a behavior test
(ZeroDivisionError, StopIteration, TypeError, lost ordering, a dropped guard).
Only a careful, behavior-preserving simplification is both structurally clean and
green -- so a model that simplifies carelessly scores hard=0, which de-saturates
the deterministic floor and gives the gate (and the soft process rubric, which
rewards "re-verify behavior") something real to optimize.

Three reference variants per fixture:
  code      -- cluttered, behavior-correct, structural-RED   (what the agent sees)
  naive_code -- the tempting simplification: structural-GREEN, behavior-RED (the trap)
  fix_code  -- the careful simplification: structural-GREEN, behavior-GREEN

--verify checks all three: cluttered RED, naive RED (the trap bites), fix GREEN.
naive_code and fix_code are never written into the file the agent sees.

    python fixtures/simplifying-traps/build_fixtures.py            # materialize
    python fixtures/simplifying-traps/build_fixtures.py --verify   # check the 3-way matrix
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

_HELPER = '''import ast
import inspect

import {mod} as mod


def _has(types):
    return any(isinstance(n, types) for n in ast.walk(ast.parse(inspect.getsource(mod))))


def _max_if_depth(node=None, depth=0):
    if node is None:
        node = ast.parse(inspect.getsource(mod))
    best = depth
    for child in ast.iter_child_nodes(node):
        step = 1 if isinstance(child, ast.If) else 0
        best = max(best, _max_if_depth(child, depth + step))
    return best
'''


FIXTURES: list[dict] = [
    {
        "id": "sc2-avg",
        "module": "average.py",
        "clutter_class": "manual accumulation loop guarding an empty input",
        "report": (
            "average.py works and its behavior tests pass, but mean_or_zero() accumulates "
            "with a manual loop. Replace the loop with a builtin WITHOUT changing behavior. A "
            "structural check (test_no_manual_loop) currently fails; make it pass while keeping "
            "every behavior test green."
        ),
        "code": '''def mean_or_zero(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    if not nums:
        return 0
    total = 0
    for n in nums:
        total += n
    return total / len(nums)
''',
        "naive_code": '''def mean_or_zero(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    return sum(nums) / len(nums)
''',
        "fix_code": '''def mean_or_zero(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    return sum(nums) / len(nums) if nums else 0
''',
        "test": '''def test_mean():
    assert mod.mean_or_zero([2, 4, 6]) == 4
    assert mod.mean_or_zero([10]) == 10


def test_empty_is_zero():
    assert mod.mean_or_zero([]) == 0


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use sum()/len(), not a manual loop"
''',
    },
    {
        "id": "sc2-firstmatch",
        "module": "find.py",
        "clutter_class": "manual first-match loop with a no-match fallback",
        "report": (
            "find.py works and its behavior tests pass, but first_even() scans with a manual "
            "loop. Replace it with a builtin WITHOUT changing behavior. A structural check "
            "(test_no_manual_loop) currently fails; make it pass while keeping every behavior "
            "test green."
        ),
        "code": '''def first_even(nums):
    """First even number in nums, or None if there is none."""
    for n in nums:
        if n % 2 == 0:
            return n
    return None
''',
        "naive_code": '''def first_even(nums):
    """First even number in nums, or None if there is none."""
    return next(n for n in nums if n % 2 == 0)
''',
        "fix_code": '''def first_even(nums):
    """First even number in nums, or None if there is none."""
    return next((n for n in nums if n % 2 == 0), None)
''',
        "test": '''def test_finds_first_even():
    assert mod.first_even([1, 3, 4, 6]) == 4


def test_no_match_is_none():
    assert mod.first_even([1, 3, 5]) is None


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use next() with a generator, not a manual loop"
''',
    },
    {
        "id": "sc2-flag",
        "module": "gate.py",
        "clutter_class": "redundant boolean branching guarding a None input",
        "report": (
            "gate.py works and its behavior tests pass, but meets() is a nest of if/else "
            "branches returning True/False. Collapse it to a single boolean expression WITHOUT "
            "changing behavior. A structural check (test_no_if) currently fails; make it pass "
            "while keeping every behavior test green."
        ),
        "code": '''def meets(value, threshold):
    """True when value is provided and at least threshold."""
    if value is not None:
        if value >= threshold:
            return True
        else:
            return False
    else:
        return False
''',
        "naive_code": '''def meets(value, threshold):
    """True when value is provided and at least threshold."""
    return value >= threshold
''',
        "fix_code": '''def meets(value, threshold):
    """True when value is provided and at least threshold."""
    return value is not None and value >= threshold
''',
        "test": '''def test_meets():
    assert mod.meets(5, 3) is True
    assert mod.meets(2, 3) is False


def test_none_is_false():
    assert mod.meets(None, 3) is False


def test_no_if():
    assert not _has((ast.If,)), "meets should be a single boolean return, no if-statements"
''',
    },
    {
        "id": "sc2-dedup",
        "module": "dedup.py",
        "clutter_class": "manual order-preserving de-duplication loop",
        "report": (
            "dedup.py works and its behavior tests pass, but unique() de-duplicates with a "
            "manual seen-set loop. Replace the loop with a builtin WITHOUT changing behavior. A "
            "structural check (test_no_manual_loop) currently fails; make it pass while keeping "
            "every behavior test green."
        ),
        "code": '''def unique(items):
    """Items with duplicates removed, original order preserved."""
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result
''',
        "naive_code": '''def unique(items):
    """Items with duplicates removed, original order preserved."""
    return list(set(items))
''',
        "fix_code": '''def unique(items):
    """Items with duplicates removed, original order preserved."""
    return list(dict.fromkeys(items))
''',
        "test": '''def test_dedup_preserves_order():
    assert mod.unique([3, 1, 3, 2, 1, 2]) == [3, 1, 2]


def test_removes_duplicates():
    assert mod.unique([5, 5, 5]) == [5]


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use dict.fromkeys(), not a manual seen-set loop"
''',
    },
    {
        "id": "sc2-nest",
        "module": "ship.py",
        "clutter_class": "nested if/else with an easily-dropped zero-weight guard",
        "report": (
            "ship.py works and its behavior tests pass, but cost() is nested if/else. Flatten "
            "it with guard clauses WITHOUT changing behavior. A structural check "
            "(test_nesting_is_flat) currently fails; make it pass while keeping every behavior "
            "test green."
        ),
        "code": '''def cost(weight, intl):
    """Shipping cost: 0 when weight is 0, else 10 domestic / 20 international."""
    if weight > 0:
        if intl:
            return 20
        return 10
    return 0
''',
        "naive_code": '''def cost(weight, intl):
    """Shipping cost: 0 when weight is 0, else 10 domestic / 20 international."""
    return 20 if intl else 10
''',
        "fix_code": '''def cost(weight, intl):
    """Shipping cost: 0 when weight is 0, else 10 domestic / 20 international."""
    if weight == 0:
        return 0
    return 20 if intl else 10
''',
        "test": '''def test_cost():
    assert mod.cost(5, True) == 20
    assert mod.cost(5, False) == 10


def test_zero_weight_is_free():
    assert mod.cost(0, True) == 0


def test_nesting_is_flat():
    assert _max_if_depth() <= 1, "flatten the nested if/else into guard clauses"
''',
    },
]

SPLIT_ASSIGN = {
    "train": ["sc2-avg", "sc2-firstmatch", "sc2-flag", "sc2-dedup", "sc2-nest"],
    "val":   ["sc2-avg", "sc2-firstmatch", "sc2-flag", "sc2-dedup", "sc2-nest"],
    "test":  ["sc2-flag"],
}


def _test_source(fx: dict) -> str:
    return _HELPER.format(mod=fx["module"][:-3]) + "\n\n" + fx["test"]


def _context(fx: dict) -> str:
    module = fx["module"]
    return (
        f"Workspace files:\n  {module}   (works; behavior tests pass; cluttered)\n"
        f"  test_{module}   (pytest; a structural simplicity check currently fails)\n\n"
        f"Clutter: {fx['clutter_class']}\n"
        f"Keep behavior identical -- the behavior tests guard it; the obvious one-liner may "
        f"not. Run `python -m pytest -q` to see which check fails."
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
            f.write(_test_source(fx))
    for split, ids in SPLIT_ASSIGN.items():
        split_dir = os.path.join(SPLITS, split)
        os.makedirs(split_dir, exist_ok=True)
        with open(os.path.join(split_dir, "items.json"), "w", encoding="utf-8") as f:
            json.dump([_item(by_id[i]) for i in ids], f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(FIXTURES)} trap fixtures to {TASKS}")
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
        test = _test_source(fx)
        cluttered = _run_pytest(fx["code"], test, fx["module"]) != 0      # want RED
        naive = _run_pytest(fx["naive_code"], test, fx["module"]) != 0    # want RED (trap bites)
        fixed = _run_pytest(fx["fix_code"], test, fx["module"]) == 0      # want GREEN
        good = cluttered and naive and fixed
        ok = ok and good
        print(f"  [{'OK' if good else 'BROKEN'}] {fx['id']:14} "
              f"cluttered={'RED' if cluttered else 'GREEN(!)'} "
              f"naive={'RED' if naive else 'GREEN(!)'} "
              f"fixed={'GREEN' if fixed else 'RED(!)'}")
    print("All fixtures well-formed (cluttered RED, naive RED, careful fix GREEN)." if ok
          else "SOME FIXTURES BROKEN -- do not use until fixed.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify())
    main()
