import ast
import inspect

import gate as mod


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


def test_meets():
    assert mod.meets(5, 3) is True
    assert mod.meets(2, 3) is False


def test_none_is_false():
    assert mod.meets(None, 3) is False


def test_no_if():
    assert not _has((ast.If,)), "meets should be a single boolean return, no if-statements"
