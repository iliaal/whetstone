import ast
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
