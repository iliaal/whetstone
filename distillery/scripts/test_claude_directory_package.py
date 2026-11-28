import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("package_claude_directory", REPO_ROOT / "scripts/package-claude-directory.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def test_real_build_has_no_executables_hooks_or_mcp(tmp_path):
    stage = tmp_path / "whetstone"
    result = package.build(REPO_ROOT, stage)

    assert result["counts"]["skills"] > 0
    files = [p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()]
    assert not [f for f in files if f.startswith(("hooks/", "scripts/", "evals/")) or "/scripts/" in f]
    assert "commands/ia-resolve-pr.md" not in files
    assert all(not (stage / f).read_bytes().startswith(b"#!") for f in files)
    plugin = json.loads((stage / ".claude-plugin/plugin.json").read_text())
    assert "mcpServers" not in plugin and "hooks" not in plugin
    assert f"{result['counts']['skills']} skills" in plugin["description"]


def test_real_build_leaves_source_plugin_untouched(tmp_path):
    package.build(REPO_ROOT, tmp_path / "whetstone")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "plugins/whetstone"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    ).stdout
    assert status == ""


def test_frontmatter_is_flattened_and_filtered():
    text = "---\nname: ia-x\nclass: tool\ndescription: >-\n  First line,\n  second: line.\npaths:\n  - \"**/*.c\"\n  - \"**/*.h\"\n---\nBody\n"
    out, dropped = package.normalize_frontmatter("skills/ia-x/SKILL.md", text, {"skill": ["name", "description", "paths"]})
    assert dropped == ["class"]
    assert out == '---\nname: ia-x\ndescription: "First line, second: line."\npaths: ["**/*.c", "**/*.h"]\n---\nBody\n'


def test_frontmatter_rejects_shapes_it_cannot_flatten():
    text = "---\nname: ia-x\nmetadata:\n  owner: someone\n---\n"
    with pytest.raises(package.BuildError, match="unsupported nested value"):
        package.normalize_frontmatter("skills/ia-x/SKILL.md", text, {"skill": ["name", "description"]})


def test_excluded_matches_directory_globs_and_files():
    patterns = ["hooks/", "skills/*/scripts/", "commands/ia-resolve-pr.md"]
    assert package.excluded("hooks/inject-skills.sh", patterns)
    assert package.excluded("skills/ia-debugging/scripts/collect-diagnostics.sh", patterns)
    assert package.excluded("commands/ia-resolve-pr.md", patterns)
    assert not package.excluded("skills/ia-debugging/SKILL.md", patterns)
    assert not package.excluded("skills/ia-hooks/SKILL.md", patterns)


def write_plugin(stage, files):
    for relative, content in {".claude-plugin/plugin.json": "{}", **files}.items():
        path = stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())


def test_validate_reports_each_refused_shape(tmp_path):
    write_plugin(tmp_path, {
        "tool.py": "print(1)\n",
        "notes.md": "#!/bin/sh\n",
        "skills/a/SKILL.md": "Run $CLAUDE_PLUGIN_ROOT/x and init-plan.sh; see [gone](./references/gone.md).\n",
    })
    problems = package.validate(tmp_path, {"forbidden_text": ["CLAUDE_PLUGIN_ROOT"]}, {"init-plan.sh"})
    joined = "\n".join(problems)
    assert "tool.py: file type not accepted" in joined
    assert "notes.md: starts with #!" in joined
    assert "mentions CLAUDE_PLUGIN_ROOT" in joined
    assert "mentions omitted file init-plan.sh" in joined
    assert "broken link ./references/gone.md" in joined


def test_validate_accepts_images_and_flags_zip_payloads(tmp_path):
    write_plugin(tmp_path, {"icon.png": b"\x89PNG\r\n\x1a\n\0\0", "bad.png": b"\x89PNG\0PK\x03\x04"})
    problems = package.validate(tmp_path, {"forbidden_text": []}, set())
    assert problems == ["bad.png: image holds a zip signature"]


def test_stale_patch_fails_the_build(tmp_path):
    (tmp_path / "doc.md").write_text("current text\n")
    patch = tmp_path / "doc.patch"
    patch.write_text("--- a/doc.md\n+++ b/doc.md\n@@ -1 +1 @@\n-old text\n+new text\n")
    with pytest.raises(package.BuildError, match="doc.patch no longer applies"):
        package.apply_patches(tmp_path, [patch])
