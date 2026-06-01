import ast
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
