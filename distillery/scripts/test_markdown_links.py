"""Local Markdown links through the plugin validation entry points."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import distiller
from markdown_links import broken_local_links, markdown_anchors


def test_existing_file_with_missing_fragment_is_reported(tmp_path):
    (tmp_path / "target.md").write_text("# Real section\n", encoding="utf-8")
    assert distiller._find_broken_relative_links(
        "[missing](./target.md#absent)", tmp_path
    ) == ["./target.md#absent"]


@pytest.mark.parametrize("heading, anchor", [
    ("## Escaped \\*marker\\* and `under_score`", "escaped-marker-and-under_score"),
    ("## [Visible label](https://example.com/hidden) &amp; **text**", "visible-label--text"),
    ("## Résumé 你好 e\u0301 — state", "résumé-你好-e\u0301--state"),
    ("## Three   spaces", "three---spaces"),
    ("## &#x20;edge&#x20;", "-edge-"),
    ("Setext heading\n===", "setext-heading"),
    ("> ## Quoted heading", "quoted-heading"),
    ("<h2>HTML <em>heading</em></h2>", "html-heading"),
])
def test_anchors_follow_rendered_heading_text(heading, anchor):
    assert anchor in markdown_anchors(heading)


def test_duplicate_slugs_skip_all_previously_used_heading_ids():
    text = "# Echo\n# Echo\n# Echo 1\n# Echo-1\n# Echo\n"
    assert markdown_anchors(text) == {"echo", "echo-1", "echo-1-1", "echo-1-2", "echo-2"}


def test_explicit_anchors_are_case_sensitive_and_do_not_number_headings():
    text = '<a name="Section"></a>\n<a id="section-1"></a>\n\n# Section\n# Section\n'
    assert markdown_anchors(text) == {"Section", "section", "section-1"}


def test_code_comments_and_frontmatter_do_not_create_anchors():
    text = (
        '---\nname: demo\ndescription: "# Header"\n---\n'
        '<!-- <a name="comment"></a> -->\n'
        '`<a name="inline"></a>`\n\n'
        '~~~md\n# Fenced\n<a name="fenced"></a>\n~~~\n\n'
        '    # Indented\n    <a name="indented"></a>\n\n'
        '# Real `under_score`\n'
    )
    assert markdown_anchors(text) == {"real-under_score"}


def test_same_file_links_require_exact_fragment(tmp_path):
    text = '# Real\n<a name="ExactCase"></a>\n\n[good](#real) [good](#ExactCase) [bad](#Real) [bad](#exactcase)'
    assert broken_local_links(text, tmp_path) == [
        ("#Real", "missing fragment"), ("#exactcase", "missing fragment")
    ]


def test_decoded_paths_fragments_reference_links_and_titles(tmp_path):
    (tmp_path / "file name(1)#.md").write_text("# Café\n", encoding="utf-8")
    text = (
        '[one](<./file%20name(1)%23.md#caf%C3%A9> "optional title")\n'
        '[two][target]\n\n[target]: ./file%20name(1)%23.md#caf%C3%A9\n'
    )
    assert broken_local_links(text, tmp_path) == []


def test_filenames_and_non_markdown_fragments_keep_existing_behavior(tmp_path):
    (tmp_path / "target.md").write_text("# Real\n", encoding="utf-8")
    (tmp_path / "image.svg").write_text("<svg></svg>", encoding="utf-8")
    text = '[file](./target.md) ![asset](./image.svg#icon) [bad](./missing.md) ![bad](./missing.svg)'
    assert broken_local_links(text, tmp_path) == [
        ("./missing.md", "missing file"), ("./missing.svg", "missing file")
    ]


def test_resource_link_must_be_a_file(validation_repo):
    _, skill, refs = validation_repo
    (refs / "directory.md").mkdir()
    assert broken_local_links('[bad](./references/directory.md#real)', skill) == [
        ("./references/directory.md#real", "missing file")
    ]


def test_external_links_and_illustrative_code_are_not_local_links(tmp_path):
    text = (
        '[remote](https://example.com/missing.md#absent) [remote](//example.com/a.md#absent)\n'
        '[mail](mailto:person@example.com)\n'
        '`[example](./inline.md#fake)`\n\n'
        '````md\n[example](./fenced.md#fake)\n```\n# Still fenced\n````\n\n'
        '    [example](./indented.md#fake)\n'
    )
    assert broken_local_links(text, tmp_path) == []


@pytest.fixture
def validation_repo(tmp_path):
    root = tmp_path / "repo"
    plugin = root / "plugins" / "whetstone"
    skill = plugin / "skills" / "ia-demo"
    refs = skill / "references"
    refs.mkdir(parents=True)
    for directory in ("agents", "commands", "hooks"):
        (plugin / directory).mkdir()
    for name in ("distiller.py", "markdown_links.py"):
        destination = root / "distillery" / "scripts" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(__file__).parent / name, destination)
    shell = root / "scripts" / "validate-cross-refs.sh"
    shell.parent.mkdir()
    shutil.copy2(Path(__file__).parents[2] / "scripts" / shell.name, shell)
    (root / "README.md").write_text("# Repo\n", encoding="utf-8")
    (plugin / "README.md").write_text("# Plugin\n", encoding="utf-8")
    for directory in ("agents", "commands"):
        (plugin / directory / "ia-demo.md").write_text(
            "---\nname: ia-demo\ndescription: Use when validating a fixture command.\n---\n# Demo\n",
            encoding="utf-8",
        )
    (plugin / "hooks" / "skill-patterns.sh").write_text("", encoding="utf-8")
    (skill / "SKILL.md").write_text(
        "---\nname: ia-demo\nclass: tool\ndescription: Use when validating a fixture skill.\n---\n"
        "# Fixture\n\n" + "Exercise a documented local link without changing unrelated behavior. " * 50
        + "\n\n[Target](./references/target.md#real)\n",
        encoding="utf-8",
    )
    (refs / "target.md").write_text("# Real\n", encoding="utf-8")
    return root, skill, refs


def _validate_cli(root):
    return subprocess.run(
        [sys.executable, str(root / "distillery/scripts/distiller.py"), "validate-plugin", "--component", "ia-demo"],
        capture_output=True, text=True, timeout=20,
    )


@pytest.mark.parametrize("source", ["SKILL.md", "reference", "same-file"])
def test_distiller_cli_reports_missing_fragment(validation_repo, source):
    root, skill, refs = validation_repo
    path = skill / "SKILL.md" if source == "SKILL.md" else refs / "target.md"
    link = "#absent" if source == "same-file" else "./target.md#absent"
    if source == "SKILL.md":
        link = "./references/target.md#absent"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[bad]({link})\n")
    result = _validate_cli(root)
    report = json.loads(result.stdout)
    findings = [entry for entry in report["findings"] if entry["check"] == "BROKEN_REFERENCE_LINK"]
    assert len(findings) == 1
    assert f"missing fragment: {link}" in findings[0]["message"]


def test_skill_fragment_link_does_not_make_reference_an_orphan(validation_repo):
    root, _, _ = validation_repo
    result = _validate_cli(root)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert not any(entry["check"] in {"BROKEN_REFERENCE_LINK", "ORPHAN_REFERENCE"}
                   for entry in report["findings"])


def test_bash_gate_accepts_then_rejects_missing_fragment(validation_repo):
    root, _, refs = validation_repo
    command = ["bash", str(root / "scripts/validate-cross-refs.sh")]
    good = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert good.returncode == 0, good.stdout + good.stderr
    (refs / "target.md").write_text("# Real\n[bad](#absent)\n", encoding="utf-8")
    bad = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "missing fragment: #absent" in bad.stdout
    assert "FAILED" in bad.stdout


def test_missing_parser_dependency_fails_loudly(validation_repo):
    root, _, refs = validation_repo
    result = subprocess.run(
        [sys.executable, "-S", str(root / "distillery/scripts/markdown_links.py"), str(refs)],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "requires markdown-it-py" in result.stderr
    assert "Traceback" not in result.stderr


def test_empty_markdown_scope_is_not_a_successful_check(validation_repo, tmp_path):
    root, _, _ = validation_repo
    empty = tmp_path / "empty"
    empty.mkdir()
    result = subprocess.run(
        [sys.executable, str(root / "distillery/scripts/markdown_links.py"), str(empty)],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 2
    assert "no Markdown files" in result.stderr


def test_root_relative_links_resolve_from_repository_root(validation_repo):
    root, skill, _ = validation_repo
    target = "/plugins/whetstone/skills/ia-demo/references/target.md#real"
    with (skill / "SKILL.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n[good]({target})\n")
    result = _validate_cli(root)
    report = json.loads(result.stdout)
    assert not any(entry["check"] == "BROKEN_REFERENCE_LINK" for entry in report["findings"])
    gate = subprocess.run(
        ["bash", str(root / "scripts/validate-cross-refs.sh")],
        capture_output=True, text=True, timeout=20,
    )
    assert gate.returncode == 0, gate.stdout + gate.stderr


def test_root_relative_resource_link_is_not_an_orphan(validation_repo):
    root, skill, _ = validation_repo
    path = skill / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "./references/target.md#real", "/plugins/whetstone/skills/ia-demo/references/target.md#real"
    ), encoding="utf-8")
    report = json.loads(_validate_cli(root).stdout)
    assert not any(entry["check"] in {"BROKEN_REFERENCE_LINK", "ORPHAN_REFERENCE"}
                   for entry in report["findings"])


@pytest.mark.parametrize("kind", ["agents", "commands"])
def test_distiller_cli_checks_agent_and_command_fragments(validation_repo, kind):
    root, _, _ = validation_repo
    path = root / "plugins/whetstone" / kind / "ia-demo.md"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n[bad](#absent)\n")
    report = json.loads(_validate_cli(root).stdout)
    findings = [entry for entry in report["findings"] if entry["check"] == "BROKEN_REFERENCE_LINK"]
    assert len(findings) == 1
    assert "missing fragment: #absent" in findings[0]["message"]


def test_bash_gate_resolves_plugin_readme_root_relative_link(validation_repo):
    root, _, _ = validation_repo
    (root / "plugins/whetstone/README.md").write_text(
        "# Plugin\n[agent](/plugins/whetstone/agents/ia-demo.md#demo)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(root / "scripts/validate-cross-refs.sh")],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
