import re
import subprocess
from pathlib import Path

import pytest


SKILLS = Path(__file__).resolve().parents[2] / "plugins/whetstone/skills"


@pytest.mark.parametrize("a,b", [(1, "payload"), (0, "payload"), ([], True), (True, True)])
def test_boolean_simplification_preserves_type_and_value(a, b):
    text = (SKILLS / "ia-simplifying-code/references/simplification-patterns.md").read_text()
    row = next(line for line in text.splitlines() if line.startswith("| Boolean-returning"))
    expression = re.search(r"`return ([^`]+)`", row).group(1)
    result = eval(expression, {}, {"a": a, "b": b})
    assert type(result) is bool
    assert result == (True if a and b else False)


def test_boolean_simplification_preserves_custom_truthiness_evaluations():
    text = (SKILLS / "ia-simplifying-code/references/simplification-patterns.md").read_text()
    row = next(line for line in text.splitlines() if line.startswith("| Boolean-returning"))
    expression = re.search(r"`return ([^`]+)`", row).group(1)

    class ChangingTruth:
        calls = 0

        def __bool__(self):
            self.calls += 1
            return self.calls > 1

    value = ChangingTruth()
    result = eval(expression, {}, {"a": value, "b": True})
    assert result is False
    assert value.calls == 1
