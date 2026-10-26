"""Starter specifications must not invent evidence of completed validation."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

import distiller


GENERATOR = Path(__file__).resolve().parents[2] / "scripts/generate-spec.py"


@pytest.mark.parametrize("examples_per_label", [None, 4, 5, 6])
@pytest.mark.parametrize("reference_count", [0, 2])
def test_starter_coverage_requires_verification(tmp_path, examples_per_label, reference_count):
    skill = "ia-example"
    skill_dir = tmp_path / "plugins/whetstone/skills" / skill
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: ia-example\ndescription: Check example input.\n"
        "class: discipline\n---\n# Procedure\n", encoding="utf-8")
    for index in range(reference_count):
        reference = skill_dir / "references" / f"example-{index}.md"
        reference.parent.mkdir(exist_ok=True)
        reference.write_text("# Example\n", encoding="utf-8")
    if examples_per_label is not None:
        fixture = tmp_path / "distillery/tests/fixtures/triggers" / f"{skill}.jsonl"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("\n".join(
            json.dumps({"prompt": f"{label} example {index}", "expect": label})
            for label in (True, False) for index in range(examples_per_label)
        ), encoding="utf-8")
        # Presence alone proves neither matching behavior nor a passing test.
        patterns = tmp_path / "plugins/whetstone/hooks/skill-patterns.sh"
        patterns.parent.mkdir()
        patterns.write_text("SKILL_PATTERNS[ia-example]='never-match'\n", encoding="utf-8")

    result = subprocess.run([sys.executable, str(GENERATOR)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    spec = (skill_dir / "SPEC.md").read_text(encoding="utf-8")
    # Use the actual downstream parser and action contract, not copied tokens.
    rows = distiller._parse_coverage_matrix(spec)
    assert [row[0] for row in rows] == [
        "Trigger fixtures", "Hook regex pattern", "Reference architecture", "Real-usage signal",
    ]
    for dimension, status, evidence in rows:
        if dimension == "Reference architecture" and reference_count == 0:
            assert status == "n/a"
            assert evidence == "no Markdown files under references/"
        else:
            assert status == "unknown", (dimension, status)
            assert distiller._coverage_status_is_partial(status)
            assert distiller._coverage_row_has_action(evidence), (dimension, evidence)
    assert rows[0][2] == (
        f"Add or review distillery/tests/fixtures/triggers/{skill}.jsonl "
        "(>=5 should_trigger, >=5 should_not_trigger), then test with "
        f"`python3 distillery/scripts/distiller.py test-triggers --skill {skill}` and record the result."
    )
    assert rows[1][2] == (
        f"Confirm `SKILL_PATTERNS[{skill}]` in plugins/whetstone/hooks/skill-patterns.sh, "
        f"then test with `python3 distillery/scripts/distiller.py test-triggers --skill {skill}` "
        "and record the result."
    )
    if reference_count:
        assert rows[2][2] == (
            f"Review {reference_count} file(s) under references/ and validate their routing from SKILL.md."
        )
    assert rows[3][2] == (
        "Collect real-usage evidence with `python3 distillery/scripts/distiller.py "
        f"harvest-sessions --skill {skill}`, then review distillery/.eval-data/{skill}/ "
        "and record coverage or remaining gaps."
    )

    # Rerunning the scaffold must never overwrite a maintainer's verified result.
    verified = spec.replace("| Trigger fixtures | unknown |", "| Trigger fixtures | complete |")
    (skill_dir / "SPEC.md").write_text(verified, encoding="utf-8")
    rerun = subprocess.run([sys.executable, str(GENERATOR)], cwd=tmp_path,
                           capture_output=True, text=True, timeout=10)
    assert rerun.returncode == 0, rerun.stderr
    assert (skill_dir / "SPEC.md").read_text(encoding="utf-8") == verified
