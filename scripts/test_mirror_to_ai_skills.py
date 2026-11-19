"""Exercise the mirror only against disposable repositories under a fake HOME."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).with_name("mirror-to-ai-skills.sh")


@pytest.fixture
def mirror(tmp_path):
    repo = tmp_path / "source"
    script = repo / "scripts" / SCRIPT.name
    script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script)
    source = repo / "plugins/whetstone/skills"
    source.mkdir(parents=True)
    (repo / "LICENSE").write_text("fixture license\n")
    home = tmp_path / "home"
    target = home / "ai/ai-skills"
    (target / "skills").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "master", str(target)], check=True)
    staging = tmp_path / "staging"
    staging.mkdir()
    env = dict(os.environ, HOME=str(home), TMPDIR=str(staging))

    def run(*args, check=True):
        result = subprocess.run(["bash", str(script), *args], env=env,
                                text=True, capture_output=True, check=check)
        assert list(staging.iterdir()) == []
        return result

    return source, target, run


def skill(source, name):
    folder = source / name
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\nBody\n")
    (folder / "references/guide.md").write_text("original\n")
    return folder


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_ino,
                                      p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


@pytest.mark.parametrize("name", ["ia-example", "example"])
def test_second_run_and_dry_run_are_noops(mirror, name):
    source, target, run = mirror
    folder = skill(source, name)
    cache = folder / "scripts/__pycache__"
    cache.mkdir(parents=True)
    (cache / "helper.pyc").write_bytes(b"bytecode")
    assert "Added:     1" in run().stdout
    assert (target / "skills/example/SKILL.md").read_text() == "---\nname: example\n---\nBody\n"
    assert not list(target.rglob("__pycache__"))
    before = snapshot(target)
    (cache / "helper.pyc").write_bytes(b"new bytecode")
    for args in [(), ("--dry-run",)]:
        output = run(*args).stdout
        assert "Updated:   0" in output
        assert "Unchanged: 1" in output
        assert snapshot(target) == before


@pytest.mark.parametrize("change", ["add", "change", "remove"])
def test_reference_changes_are_mirrored(mirror, change):
    source, target, run = mirror
    folder = skill(source, "ia-example")
    run()
    ref = folder / "references/guide.md"
    if change == "add":
        (folder / "references/second.md").write_text("new\n")
    elif change == "change":
        ref.write_text("changed\n")
    else:
        ref.unlink()
    before = snapshot(target)
    assert "Updated:   1" in run("--dry-run").stdout
    assert snapshot(target) == before
    assert "Updated:   1" in run().stdout
    expected = {p.name: p.read_bytes() for p in (folder / "references").iterdir()}
    assert {p.name: p.read_bytes() for p in (target / "skills/example/references").iterdir()} == expected
    assert "Unchanged: 1" in run().stdout


def test_staging_cleanup_on_normalization_failure(mirror):
    source, target, run = mirror
    folder = skill(source, "ia-example")
    run()
    before = snapshot(target)
    # The source link resolves, but its sibling is outside the staged skill.
    (source / "shared.md").write_text("---\nname: ia-example\n---\n")
    (folder / "SKILL.md").unlink()
    (folder / "SKILL.md").symlink_to("../shared.md")
    result = run(check=False)
    assert result.returncode != 0
    assert snapshot(target) == before


@pytest.mark.parametrize("args", [(), ("--dry-run",)])
@pytest.mark.parametrize("root_kind", ["missing", "file"])
def test_unavailable_source_preserves_target(mirror, args, root_kind):
    source, target, run = mirror
    skill(source, "ia-example")
    run()
    before = snapshot(target)
    shutil.rmtree(source)
    if root_kind == "file":
        source.write_text("not a source directory\n")
    result = run(*args, check=False)
    assert result.returncode != 0
    assert "Source directory does not exist" in result.stderr
    assert snapshot(target) == before


@pytest.mark.parametrize("name", ["ia-example", "example"])
def test_missing_skill_file_retires_mirror(mirror, name):
    source, target, run = mirror
    folder = skill(source, name)
    run()
    (folder / "SKILL.md").unlink()
    before = snapshot(target)
    assert "Removed:   1" in run("--dry-run").stdout
    assert snapshot(target) == before
    assert "Removed:   1" in run().stdout
    assert not (target / "skills/example").exists()
    assert (folder / "references/guide.md").read_text() == "original\n"


@pytest.mark.parametrize("valid_name", ["ia-example", "example"])
def test_valid_alternate_source_keeps_mirror(mirror, valid_name):
    source, target, run = mirror
    skill(source, valid_name)
    invalid_name = "example" if valid_name == "ia-example" else "ia-example"
    (source / invalid_name).mkdir()
    run()
    before = snapshot(target)
    for args in [("--dry-run",), ()]:
        assert "Removed:   0" in run(*args).stdout
        assert snapshot(target) == before


def test_empty_valid_source_still_retires_mirror(mirror):
    source, target, run = mirror
    folder = skill(source, "ia-example")
    run()
    shutil.rmtree(folder)
    before = snapshot(target)
    assert "Removed:   1" in run("--dry-run").stdout
    assert snapshot(target) == before
    assert "Removed:   1" in run().stdout
    assert not (target / "skills/example").exists()
