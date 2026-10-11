import shutil
import subprocess
from pathlib import Path

import pytest


GENERATOR = Path(__file__).resolve().parents[2] / "scripts" / "generate-skill-hooks.sh"


def run_generator(tmp_path, content, *, force=False, previous=None, symlink=False):
    repo = tmp_path / "fixture repository"
    script = repo / "scripts" / GENERATOR.name
    script.parent.mkdir(parents=True)
    shutil.copyfile(GENERATOR, script)
    skill = repo / "plugins" / "whetstone" / "skills" / "ia-fixture" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(content.encode())
    output_name = "skill-patterns.sh" if force else "skill-patterns.draft.sh"
    draft = repo / "plugins" / "whetstone" / "hooks" / output_name
    if previous is not None:
        draft.parent.mkdir()
        if symlink:
            draft.symlink_to("existing-patterns.sh")
        draft.write_text(previous)
        draft.chmod(0o640)
    result = subprocess.run(
        ["bash", str(script), *(["--force"] if force else [])],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    return result, draft


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("final_newline", [False, True])
def test_generator_reads_only_complete_frontmatter(tmp_path, newline, final_newline):
    content = newline.join([
        "---", "name: ia-fixture",
        "description: Use when checking x --- and y.", "---",
    ])
    if final_newline:
        content += newline
    result, draft = run_generator(tmp_path, content)
    assert result.returncode == 0, result.stderr
    loaded = subprocess.run(
        ["bash", "-c", 'source "$1"; printf "%s" "${SKILL_PATTERNS[ia-fixture]}"',
         "bash", str(draft)],
        capture_output=True, text=True, timeout=5,
    )
    assert loaded.returncode == 0, loaded.stderr
    assert loaded.stdout == "checking x --- and y."
    assert "Generated 1 skill patterns" in result.stdout


@pytest.mark.parametrize("content", [
    "# Body first\n---\ndescription: Use when checking misplaced metadata.\n---\n",
    "---\ndescription: Use when checking unclosed metadata.\n",
    "---not-a-marker\ndescription: Use when checking invalid metadata.\n---\n",
])
def test_generator_rejects_missing_frontmatter_delimiters(tmp_path, content):
    result, draft = run_generator(tmp_path, content)
    assert result.returncode != 0
    assert "Invalid frontmatter" in result.stderr
    assert "ia-fixture" in result.stderr
    assert not draft.exists()


@pytest.mark.parametrize("force", [False, True])
def test_generator_preserves_existing_output_on_invalid_frontmatter(tmp_path, force):
    previous = f"# Preserve existing patterns from {tmp_path}\n"
    result, draft = run_generator(
        tmp_path, "---\ndescription: Use when checking unclosed metadata.\n",
        force=force, previous=previous,
    )
    assert result.returncode != 0
    assert draft.read_text() == previous
    assert draft.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("symlink", [False, True])
def test_generator_replaces_complete_output_and_preserves_permissions(tmp_path, force, symlink):
    previous = f"# Replace existing patterns from {tmp_path}\n"
    result, draft = run_generator(
        tmp_path, "---\ndescription: Use when checking valid metadata.\n---\n",
        force=force, previous=previous, symlink=symlink,
    )
    assert result.returncode == 0, result.stderr
    assert previous not in draft.read_text()
    assert "SKILL_PATTERNS[ia-fixture]" in draft.read_text()
    assert draft.stat().st_mode & 0o777 == 0o640
    assert draft.is_symlink() is symlink
