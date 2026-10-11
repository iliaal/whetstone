"""Regression coverage for frontmatter boundaries and skill argument substitution."""

import json

import pytest

import distiller


BODY = "# Procedure\n\n" + "Inspect the input and verify each required result.\n" * 20
FRONTMATTER = (
    "name: ia-example\n"
    "description: Use when checking input --- preserve the complete description.\n"
    "class: discipline\n"
)
SPEC = "\n".join(
    f"## {heading}\n\nFixture content.\n"
    for heading in (
        "Intent", "Scope", "Trigger Context", "Source And Evidence Model",
        "Evaluation", "Known Limitations", "Maintenance Notes",
    )
)


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    root = tmp_path / "plugins" / "whetstone"
    for kind in ("skills", "agents", "commands"):
        (root / kind).mkdir(parents=True)
    monkeypatch.setattr(distiller, "PLUGIN_DIR", root)
    return root


def write_component(plugin, kind, content):
    if kind == "skill":
        path = plugin / "skills" / "ia-example" / "SKILL.md"
        path.parent.mkdir(exist_ok=True)
        (path.parent / "SPEC.md").write_text(SPEC)
    else:
        path = plugin / f"{kind}s" / "ia-example.md"
    path.write_bytes(content.encode())
    return path


def frontmatter_findings(report):
    return [finding for finding in report["findings"] if finding["check"] == "frontmatter"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("description", [
    "Use when checking input --- preserve the complete description.",
    '"Use when checking input --- preserve the complete description."',
    ">-\n  Use when checking input --- preserve the complete description.",
])
def test_tolerant_parser_preserves_description_and_body(newline, description):
    body = "# Procedure\n\nCheck input --- and output.\n\n---\n\nKeep the body separator."
    text = (
        f"---\nname: ia-example\ndescription: {description}\nclass: discipline\n---\n\n{body}\n"
    ).replace("\n", newline)
    frontmatter, parsed_body = distiller._parse_md_frontmatter(text)
    assert frontmatter == {
        "name": "ia-example",
        "description": "Use when checking input --- preserve the complete description.",
        "class": "discipline",
    }
    assert parsed_body == body.replace("\n", newline)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_tolerant_parser_accepts_closing_marker_at_eof(newline):
    assert distiller._parse_md_frontmatter(f"---{newline}name: ia-example{newline}---") == (
        {"name": "ia-example"}, "",
    )


@pytest.mark.parametrize("kind", ["skill", "agent", "command"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_plugin_accepts_embedded_dashes_without_losing_fields(plugin, kind, newline):
    write_component(plugin, kind, f"---\n{FRONTMATTER}---\n{BODY}".replace("\n", newline))
    report = distiller.validate_plugin()
    assert report["passed"], report["findings"]


INVALID_BOUNDARIES = [
    pytest.param("# Preamble\n---\n" + FRONTMATTER + "---\n" + BODY, id="body-first"),
    pytest.param("---prefix\n" + FRONTMATTER + "---\n" + BODY, id="opening-suffix"),
    pytest.param("---\n" + FRONTMATTER + BODY, id="unclosed"),
    pytest.param("---\n" + FRONTMATTER + "---suffix\n" + BODY, id="closing-suffix"),
    pytest.param("---\n" + FRONTMATTER + " ---\n" + BODY, id="indented-closing"),
]


@pytest.mark.parametrize("kind", ["skill", "agent", "command"])
@pytest.mark.parametrize("content", INVALID_BOUNDARIES)
def test_plugin_reports_missing_standalone_delimiters(plugin, kind, content):
    write_component(plugin, kind, content)
    report = distiller.validate_plugin()
    errors = frontmatter_findings(report)
    assert len(errors) == 1, report["findings"]
    assert errors[0]["severity"] == "HIGH"
    assert not report["passed"]


@pytest.mark.parametrize("content", INVALID_BOUNDARIES)
def test_tolerant_parser_retains_entire_document_without_delimiters(content):
    assert distiller._parse_md_frontmatter(content) == ({}, content)


@pytest.mark.parametrize("kind", ["skill", "agent", "command"])
@pytest.mark.parametrize("header,diagnostic", [
    ("description: Reviews: everything.\n", "mapping values are not allowed"),
    ("a scalar\n", "mapping"),
    ("[one, two]\n", "mapping"),
    ("42\n", "mapping"),
    ("false\n", "mapping"),
    ("null\n", "mapping"),
    ("", "mapping"),
])
def test_plugin_reports_actual_yaml_error_without_crashing(plugin, kind, header, diagnostic):
    write_component(plugin, kind, f"---\n{header}---\n{BODY}")
    report = distiller.validate_plugin()
    errors = frontmatter_findings(report)
    assert len(errors) == 1, report["findings"]
    assert errors[0]["severity"] == "HIGH"
    assert diagnostic in errors[0]["message"]
    assert not report["passed"]


@pytest.mark.parametrize("header", ["description: Reviews: everything.\n", "[one, two]\n", "null\n"])
def test_tolerant_parser_keeps_body_when_yaml_is_invalid(header):
    assert distiller._parse_md_frontmatter(f"---\n{header}---\n\n{BODY}") == ({}, BODY.strip())


def test_yaml_comments_before_closing_marker_remain_valid(plugin):
    write_component(plugin, "skill", f"---\n{FRONTMATTER}\n## Header comment\n---\n{BODY}")
    report = distiller.validate_plugin()
    assert report["passed"], report["findings"]


@pytest.fixture
def generated_skill(tmp_path, monkeypatch):
    monkeypatch.setattr(distiller, "GENERATED_DIR", tmp_path)
    skill_dir = tmp_path / "ia-example"
    skill_dir.mkdir()
    (skill_dir / "manifest.json").write_text(json.dumps({
        "search_queries": ["example"], "sources": [{"id": "fixture/example/skill", "sha1": "abc"}],
    }))
    return skill_dir / "SKILL.md"


def test_generated_validation_counts_complete_description_and_body(generated_skill):
    description = "Use when checking input --- " + "description " * 100
    generated_skill.write_text(f"---\nname: ia-example\ndescription: {description}\n---\n{BODY}")
    report = distiller.validate("ia-example")
    assert report["gates"]["frontmatter"]["pass"]
    assert not report["gates"]["description"]["pass"]
    assert report["body_tokens"] == distiller.count_tokens(BODY.strip())


@pytest.mark.parametrize("content", INVALID_BOUNDARIES + [
    pytest.param("---\n[one, two]\n---\n" + BODY, id="yaml-sequence"),
])
def test_generated_validation_rejects_invalid_frontmatter(generated_skill, content):
    generated_skill.write_text(content)
    report = distiller.validate("ia-example")
    assert not report["gates"]["frontmatter"]["pass"]
    assert not report["valid"]


def test_keywords_include_entire_yaml_description_only():
    text = (
        '---\nname: ia-example\ndescription: "Calibration --- widgets and sensors"\n'
        'metadata:\n  unrelated: glitter\n---\nname: body-only\n'
    )
    keywords = distiller._extract_skill_keywords(text)
    assert {"calibration", "widgets", "sensors", "example"} <= keywords
    assert not {"glitter", "body", "only"} & keywords


@pytest.mark.parametrize("skill_name,task_input", [
    ("ia-react-frontend", "Fix JSX rendering in src/App.tsx."),
    ("ia-cpp-systems", "Update CMakeLists.txt so src/parser.cxx and include/parser.hpp compile."),
])
def test_shipped_skill_paths_keep_filename_tasks_relevant(skill_name, task_input):
    skill_path = distiller.PLUGIN_DIR / "skills" / skill_name / "SKILL.md"
    keywords = distiller._extract_skill_keywords(skill_path.read_text())
    relevant, overlap = distiller._check_skill_relevance(task_input, keywords)
    assert relevant, (skill_name, task_input, overlap)


@pytest.mark.parametrize("content", INVALID_BOUNDARIES)
def test_keywords_do_not_treat_broken_frontmatter_as_metadata(content):
    assert distiller._extract_skill_keywords(content) == set()


@pytest.mark.parametrize("placeholder", [f"${index}" for index in range(10)] + ["$ARGUMENTS"])
@pytest.mark.parametrize("context", ["Run {token}.", "Never use `{token}`.", "```bash\necho {token}\n```"])
def test_skill_positional_placeholders_are_high_even_in_examples(plugin, placeholder, context):
    write_component(plugin, "skill", f"---\n{FRONTMATTER}---\n{BODY}\n" + context.format(token=placeholder))
    report = distiller.validate_plugin()
    hits = [finding for finding in report["findings"] if finding["check"] == "POSITIONAL_PLACEHOLDER"]
    assert len(hits) == 1, report["findings"]
    assert hits[0]["severity"] == "HIGH"
    assert placeholder in hits[0]["message"]
    assert not report["passed"]


def test_positional_check_is_scoped_to_skill_body(plugin):
    placeholders = " ".join(f"${index}" for index in range(10)) + " $ARGUMENTS"
    path = write_component(plugin, "skill", (
        f"---\n{FRONTMATTER}argument-hint: '{placeholders}'\n---\n{BODY}\n"
        "Read [arguments](./references/arguments.md).\n"
        '```bash\necho "$PATH" "$HOME" "$SKILL_DIR" "${BASH_SOURCE[0]}" "$@"\n```\n'
    ))
    references = path.parent / "references"
    references.mkdir()
    (references / "arguments.md").write_text(placeholders)
    write_component(plugin, "agent", f"---\n{FRONTMATTER}---\n{BODY}\n{placeholders}")
    write_component(plugin, "command", f"---\n{FRONTMATTER}---\n{BODY}\n{placeholders}")
    report = distiller.validate_plugin()
    assert report["passed"], report["findings"]
