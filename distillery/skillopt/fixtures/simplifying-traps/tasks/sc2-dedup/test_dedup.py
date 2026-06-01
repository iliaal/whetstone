import ast
import inspect

import dedup as mod


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


def test_dedup_preserves_order():
    assert mod.unique([3, 1, 3, 2, 1, 2]) == [3, 1, 2]


def test_removes_duplicates():
    assert mod.unique([5, 5, 5]) == [5]


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use dict.fromkeys(), not a manual seen-set loop"
