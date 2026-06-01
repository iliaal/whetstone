import ast
import inspect

import ship as mod


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


def test_cost():
    assert mod.cost(5, True) == 20
    assert mod.cost(5, False) == 10


def test_zero_weight_is_free():
    assert mod.cost(0, True) == 0


def test_nesting_is_flat():
    assert _max_if_depth() <= 1, "flatten the nested if/else into guard clauses"
