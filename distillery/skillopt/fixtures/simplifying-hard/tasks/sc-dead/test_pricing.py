import ast
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
