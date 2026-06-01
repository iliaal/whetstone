import ast
import inspect

import average as mod


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


def test_mean():
    assert mod.mean_or_zero([2, 4, 6]) == 4
    assert mod.mean_or_zero([10]) == 10


def test_empty_is_zero():
    assert mod.mean_or_zero([]) == 0


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use sum()/len(), not a manual loop"
