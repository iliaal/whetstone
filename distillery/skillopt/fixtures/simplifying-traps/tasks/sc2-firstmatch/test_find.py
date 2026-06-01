import ast
import inspect

import find as mod


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


def test_finds_first_even():
    assert mod.first_even([1, 3, 4, 6]) == 4


def test_no_match_is_none():
    assert mod.first_even([1, 3, 5]) is None


def test_no_manual_loop():
    assert not _has((ast.For, ast.While)), "use next() with a generator, not a manual loop"
