import ast
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
