import ast
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
