#!/usr/bin/env python3
"""Materialize the ia-simplifying-code fixture task set.

Same shape and harness as fixtures/debugging-hard/ -- the agent edits one module
in a workspace and `python -m pytest -q` decides hard (rc == 0 -> all green).
The twist: each module is already behavior-correct, so the *behavior* tests pass
from the start. What is RED on the cluttered version is a deterministic
STRUCTURAL check (an AST assertion: no redundant branching, no manual loop, no
unused locals, bounded nesting, no duplicated normalization). A faithful
simplification flips that check to green WITHOUT breaking a behavior test.

This is why ia-simplifying-code reuses the debugging evaluator unchanged: "did
complexity actually drop" is encoded as a pytest assertion, so hard stays a pure
red->green signal. The process-quality judgment (did it declutter idiomatically,
not just satisfy the metric) lives in the soft rubric, not here.

    python fixtures/simplifying-hard/build_fixtures.py            # materialize
    python fixtures/simplifying-hard/build_fixtures.py --verify   # check red/green

`fix_code` is the reference simplification, used only by --verify; it is never
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
        "id": "sc-flag",
        "module": "access.py",
        "clutter_class": "redundant boolean branching (if/else returning True/False)",
        "goal_note": "the whole predicate is one boolean expression; nested if/else returning literals collapses to `return age >= 18 and not banned and verified`.",
        "report": (
            "access.py works and its behavior tests pass, but can_access() is written as a "
            "nest of if/else branches that each return True or False. Simplify it to the "
            "equivalent single boolean expression WITHOUT changing behavior. A structural "
            "check (test_no_redundant_branching) currently fails because the function still "
            "uses if-statements; make it pass while keeping every behavior test green."
        ),
        "code": '''def can_access(age, banned, verified):
    """True only for verified, non-banned adults."""
    if age >= 18:
        if banned:
            return False
        else:
            if verified:
                return True
            else:
                return False
    else:
        return False
''',
        "fix_code": '''def can_access(age, banned, verified):
    """True only for verified, non-banned adults."""
    return age >= 18 and not banned and verified
''',
        "test": '''import ast
import inspect

import access as mod


def _node_count(types):
    tree = ast.parse(inspect.getsource(mod))
    return sum(isinstance(n, types) for n in ast.walk(tree))


def test_truth_table():
    assert mod.can_access(20, False, True) is True
    assert mod.can_access(17, False, True) is False
    assert mod.can_access(20, True, True) is False
    assert mod.can_access(20, False, False) is False


def test_no_redundant_branching():
    assert _node_count((ast.If,)) == 0, "can_access should be a single boolean return, no if-statements"
''',
    },
    {
        "id": "sc-loop",
        "module": "stats.py",
        "clutter_class": "manual accumulation loop instead of a builtin/comprehension",
        "goal_note": "the accumulator-plus-for-loop is `sum(n * n for n in nums if n % 2 == 0)`.",
        "report": (
            "stats.py works and its behavior tests pass, but sum_even_squares() builds its "
            "result with a manual accumulator loop. Replace the loop with a builtin + "
            "generator expression WITHOUT changing behavior. A structural check "
            "(test_no_manual_loop) currently fails because a for-loop is still present; make "
            "it pass while keeping every behavior test green."
        ),
        "code": '''def sum_even_squares(nums):
    """Sum the squares of the even numbers in nums."""
    total = 0
    for n in nums:
        if n % 2 == 0:
            total = total + n * n
    return total
''',
        "fix_code": '''def sum_even_squares(nums):
    """Sum the squares of the even numbers in nums."""
    return sum(n * n for n in nums if n % 2 == 0)
''',
        "test": '''import ast
import inspect

import stats as mod


def _node_count(types):
    tree = ast.parse(inspect.getsource(mod))
    return sum(isinstance(n, types) for n in ast.walk(tree))


def test_sum_even_squares():
    assert mod.sum_even_squares([1, 2, 3, 4]) == 20
    assert mod.sum_even_squares([]) == 0
    assert mod.sum_even_squares([1, 3, 5]) == 0
    assert mod.sum_even_squares([2]) == 4


def test_no_manual_loop():
    assert _node_count((ast.For, ast.While)) == 0, "use sum() + a generator, not a manual loop"
''',
    },
    {
        "id": "sc-dead",
        "module": "pricing.py",
        "clutter_class": "variables assigned but never used (dead code)",
        "goal_note": "`tax` and `note` are computed and never read; the if/else clamp is `max(discounted, 0)`.",
        "report": (
            "pricing.py works and its behavior tests pass, but final_price() assigns local "
            "variables that are never used and clamps with a verbose if/else. Remove the dead "
            "locals (and tidy the clamp) WITHOUT changing behavior. A structural check "
            "(test_no_unused_locals) currently fails because of the unused assignments; make "
            "it pass while keeping every behavior test green."
        ),
        "code": '''def final_price(base, discount):
    """Apply a percentage discount, clamped to >= 0."""
    tax = base * 0.0
    discounted = base - base * discount / 100
    note = "computed"
    if discounted < 0:
        discounted = 0
    else:
        discounted = discounted
    return discounted
''',
        "fix_code": '''def final_price(base, discount):
    """Apply a percentage discount, clamped to >= 0."""
    discounted = base - base * discount / 100
    return max(discounted, 0)
''',
        "test": '''import ast
import inspect

import pricing as mod


def _unused_locals():
    tree = ast.parse(inspect.getsource(mod))
    stored, loaded = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Store):
                stored.add(n.id)
            elif isinstance(n.ctx, ast.Load):
                loaded.add(n.id)
    return {x for x in (stored - loaded) if not x.startswith("_")}


def test_final_price():
    assert mod.final_price(100, 10) == 90
    assert mod.final_price(100, 0) == 100
    assert mod.final_price(100, 150) == 0


def test_no_unused_locals():
    assert _unused_locals() == set(), "remove variables that are assigned but never used"
''',
    },
    {
        "id": "sc-nest",
        "module": "shipping.py",
        "clutter_class": "deep if-nesting instead of guard clauses",
        "goal_note": "three levels of nested if/else flatten to a guard clause plus additive adjustments.",
        "report": (
            "shipping.py works and its behavior tests pass, but shipping_cost() is three "
            "if-levels deep. Flatten it (guard clause for the zero-weight case, then additive "
            "adjustments) WITHOUT changing behavior. A structural check (test_nesting_is_flat) "
            "currently fails because the if-nesting is too deep; make it pass while keeping "
            "every behavior test green."
        ),
        "code": '''def shipping_cost(weight, country, express):
    """Base 5; +10 if international; +20 if express; free when weight == 0."""
    if weight > 0:
        if country == "US":
            if express:
                return 25
            else:
                return 5
        else:
            if express:
                return 35
            else:
                return 15
    else:
        return 0
''',
        "fix_code": '''def shipping_cost(weight, country, express):
    """Base 5; +10 if international; +20 if express; free when weight == 0."""
    if weight == 0:
        return 0
    cost = 5
    if country != "US":
        cost += 10
    if express:
        cost += 20
    return cost
''',
        "test": '''import ast
import inspect

import shipping as mod


def _max_if_depth(node=None, depth=0):
    if node is None:
        node = ast.parse(inspect.getsource(mod))
    best = depth
    for child in ast.iter_child_nodes(node):
        step = 1 if isinstance(child, ast.If) else 0
        best = max(best, _max_if_depth(child, depth + step))
    return best


def test_cost_matrix():
    assert mod.shipping_cost(0, "US", False) == 0
    assert mod.shipping_cost(2, "US", False) == 5
    assert mod.shipping_cost(2, "US", True) == 25
    assert mod.shipping_cost(2, "DE", False) == 15
    assert mod.shipping_cost(2, "DE", True) == 35


def test_nesting_is_flat():
    assert _max_if_depth() <= 2, "flatten the nested if/else into guard clauses"
''',
    },
    {
        "id": "sc-dup",
        "module": "names.py",
        "clutter_class": "duplicated normalization logic per field",
        "goal_note": "strip()+title() is written once per field; apply it once over both via a comprehension/join.",
        "report": (
            "names.py works and its behavior tests pass, but format_full_name() repeats the "
            "same strip()+title() normalization separately for each field. De-duplicate it so "
            "the normalization appears once WITHOUT changing behavior. A structural check "
            "(test_normalization_not_duplicated) currently fails because strip/title each "
            "appear more than once; make it pass while keeping every behavior test green."
        ),
        "code": '''def format_full_name(first, last):
    """Return 'First Last' with each part trimmed and title-cased."""
    f = first.strip()
    f = f.title()
    l = last.strip()
    l = l.title()
    return f + " " + l
''',
        "fix_code": '''def format_full_name(first, last):
    """Return 'First Last' with each part trimmed and title-cased."""
    return " ".join(part.strip().title() for part in (first, last))
''',
        "test": '''import ast
import inspect

import names as mod


def _attr_calls(attr):
    tree = ast.parse(inspect.getsource(mod))
    return sum(isinstance(n, ast.Attribute) and n.attr == attr for n in ast.walk(tree))


def test_format_full_name():
    assert mod.format_full_name("  ada ", "LOVELACE") == "Ada Lovelace"
    assert mod.format_full_name("alan", "turing") == "Alan Turing"


def test_normalization_not_duplicated():
    assert _attr_calls("strip") <= 1, "the trim/case normalization should appear once, not per field"
    assert _attr_calls("title") <= 1
''',
    },
]

# train drives reflection; val drives the gate. Overlap is intentional (same as
# debugging-hard): this is a mechanics-capable set covering five clutter classes,
# so every class is seen by the gate. test holds one out for an eval_test run.
SPLIT_ASSIGN = {
    "train": ["sc-flag", "sc-loop", "sc-dead", "sc-nest", "sc-dup"],
    "val":   ["sc-flag", "sc-loop", "sc-dead", "sc-nest", "sc-dup"],
    "test":  ["sc-dead"],
}


def _context(fx: dict) -> str:
    module = fx["module"]
    return (
        f"Workspace files:\n  {module}   (works; behavior tests pass; cluttered)\n"
        f"  test_{module}   (pytest; a structural simplicity check currently fails)\n\n"
        f"Clutter: {fx['clutter_class']}\n"
        f"Keep behavior identical -- the behavior tests guard it. "
        f"Run `python -m pytest -q` to see which check fails."
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
    print(f"Wrote {len(FIXTURES)} simplify fixtures to {TASKS}")
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
        cluttered_rc = _run_pytest(fx["code"], fx["test"], fx["module"])
        fixed_rc = _run_pytest(fx["fix_code"], fx["test"], fx["module"])
        red = cluttered_rc != 0
        green = fixed_rc == 0
        status = "OK" if (red and green) else "BROKEN"
        if not (red and green):
            ok = False
        print(f"  [{status}] {fx['id']:12} cluttered={'RED' if red else 'GREEN(!)'} "
              f"simplified={'GREEN' if green else 'RED(!)'}")
    print("All fixtures well-formed (red-on-clutter, green-on-simplify)." if ok
          else "SOME FIXTURES BROKEN -- do not use until fixed.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify())
    main()
