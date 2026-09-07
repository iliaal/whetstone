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


def test_todo_example_distinguishes_complete_missing_and_pending(tmp_path):
    text = (SKILLS / "ia-file-todos/references/workflows.md").read_text()
    section = text.split("**To verify blockers are complete before starting:**", 1)[1]
    code = re.search(r"```bash\n(.*?)```", section, re.S).group(1)
    todos = tmp_path / "todos"
    todos.mkdir()
    (todos / "001-complete-p1-first task.md").touch()
    (todos / "002-ready-p1-second.md").touch()
    result = subprocess.run(["bash", "-c", code], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["Issue 002 not complete", "Issue 003 not complete"]
