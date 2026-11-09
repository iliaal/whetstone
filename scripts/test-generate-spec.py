#!/usr/bin/env python3
"""Regression checks for standalone SPEC generation (no third-party dependencies)."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("generate-spec.py")
SPEC = importlib.util.spec_from_file_location("generate_spec", SCRIPT)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class FrontmatterBoundaryTests(unittest.TestCase):
    def test_block_descriptions_preserve_prose_and_following_fields(self):
        for style in ("|", ">"):
            for indicator in ("", *map(str, range(1, 10))):
                for chomp in ("", "+", "-"):
                    for suffix in {indicator + chomp, chomp + indicator}:
                        for comment in ("", " # description"):
                            for newline in ("\n", "\r\n"):
                                with self.subTest(style=style, suffix=suffix,
                                                  comment=comment, newline=newline):
                                    indent = " " * int(indicator or 2)
                                    text = newline.join([
                                        "---", "name: ia-example",
                                        f"description: {style}{suffix}{comment}",
                                        indent + "Inspect input: preserve it.", "",
                                        indent + "---", indent + "description: still prose.",
                                        "class: workflow", "---", "# Procedure", "Body.",
                                    ])
                                    self.assertEqual(GENERATOR.parse_frontmatter(text), ({
                                        "name": "ia-example", "class": "workflow",
                                        "description": "Inspect input: preserve it. --- description: still prose.",
                                    }, newline.join(["# Procedure", "Body."])))

    def test_quoted_markers_and_plain_values_stay_inline(self):
        for value in ('"|"', "'|-2'", '">+2"', "| prose", "> prose", "Inspect: input.",
                      "|0", ">0", "|10", ">10", "|2-#comment", "|++"):
            with self.subTest(value=value):
                self.assertEqual(GENERATOR.parse_frontmatter(
                    f"---\ndescription: {value}\nclass: tool\n---\nBody"
                ), ({"description": value.strip(" '\""), "class": "tool"}, "Body"))

    def test_empty_block_descriptions_stop_at_following_field(self):
        for marker in ("|", "|-", "|+", "|2", "|2-", "|-2", ">+", ">2", ">2+", ">+2"):
            for blank in ("", "\n", "  \n\n"):
                with self.subTest(marker=marker, blank=blank):
                    self.assertEqual(GENERATOR.parse_frontmatter(
                        f"---\ndescription: {marker}\n{blank}class: tool\n---\nBody"
                    ), ({"description": "", "class": "tool"}, "Body"))

    def test_cli_renders_literal_and_indicator_descriptions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copyfile(SCRIPT, root / SCRIPT.name)
            markers = ("|", "|-", "|+", "|2", "|2-", "|-2", ">+", ">2", ">2+", ">+2 # comment", "")
            for index, marker in enumerate(markers):
                skill = root / f"plugins/whetstone/skills/ia-example-{index}"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {skill.name}\ndescription: {marker}\n"
                    "  Inspect input: preserve it.\n\n  Then validate.\n"
                    "class: workflow\n---\n# Procedure\n", encoding="utf-8")
            result = subprocess.run([sys.executable, SCRIPT.name], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            for skill in (root / "plugins/whetstone/skills").iterdir():
                with self.subTest(skill=skill.name):
                    output = (skill / "SPEC.md").read_text(encoding="utf-8")
                    self.assertIn(
                        "is a `workflow`-class skill (a multi-step process producing concrete artifacts). "
                        "Inspect input: preserve it. Then validate.\n", output)

    def test_cli_empty_descriptions_do_not_use_body_examples(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copyfile(SCRIPT, root / SCRIPT.name)
            for index, marker in enumerate(("", "|", ">", ">-", ">+", "|2", None)):
                skill = root / f"plugins/whetstone/skills/ia-example-{index}"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {skill.name}\n"
                    + (f"description: {marker}\n" if marker is not None else "")
                    + "class: tool\n---\n# Procedure\nExample only:\n"
                    "description:\n  Do not use this body example as the skill intent.\n",
                    encoding="utf-8")
            result = subprocess.run([sys.executable, SCRIPT.name], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            for skill in (root / "plugins/whetstone/skills").iterdir():
                with self.subTest(skill=skill.name):
                    output = (skill / "SPEC.md").read_text(encoding="utf-8")
                    self.assertIn("is a `tool`-class skill (a narrow utility scoped to a single capability). \n", output)
                    self.assertNotIn("Do not use this body example", output)

    def test_inline_separator_preserves_all_metadata_and_body(self):
        for newline in ("\n", "\r\n"):
            for description in ("Inspect input --- then validate.", '"Inspect --- then validate."'):
                with self.subTest(newline=repr(newline), description=description):
                    text = newline.join([
                        "---", "name: ia-example", f"description: {description}",
                        "class: discipline", "---", "# Procedure", "", "---", "Body.",
                    ])
                    metadata, body = GENERATOR.parse_frontmatter(text)
                    self.assertEqual(metadata, {
                        "name": "ia-example", "description": description.strip('"'),
                        "class": "discipline",
                    })
                    self.assertEqual(body, newline.join(["# Procedure", "", "---", "Body."]))

    def test_folded_description_keeps_inline_separator(self):
        text = "---\nname: ia-example\ndescription: >-\n  Inspect --- then\n  validate.\nclass: workflow\n---\n# Procedure\n"
        metadata, body = GENERATOR.parse_frontmatter(text)
        self.assertEqual(metadata["description"], "Inspect --- then validate.")
        self.assertEqual(metadata["class"], "workflow")
        self.assertEqual(body, "# Procedure")

    def test_folded_description_without_chomping_indicator(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                text = newline.join([
                    "---", "name: ia-example", "description: >",
                    "  Inspect --- then", "  validate.", "class: workflow",
                    "---", "# Procedure",
                ])
                metadata, body = GENERATOR.parse_frontmatter(text)
                self.assertEqual(metadata["description"], "Inspect --- then validate.")
                self.assertEqual(metadata["class"], "workflow")
                self.assertEqual(body, "# Procedure")

    def test_cli_renders_folded_description_without_chomping_indicator(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copyfile(SCRIPT, root / SCRIPT.name)
            skill = root / "plugins/whetstone/skills/ia-example"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: ia-example\ndescription: >\n"
                "  Inspect input then\n  validate it.\nclass: workflow\n---\n# Procedure\n",
                encoding="utf-8")
            result = subprocess.run([sys.executable, SCRIPT.name], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = (skill / "SPEC.md").read_text(encoding="utf-8")
            self.assertIn("Inspect input then validate it.", output)

    def test_only_standalone_delimiters_form_frontmatter(self):
        for text in ("---not a delimiter\nname: ia-example\n---\nBody",
                     "---\nname: ia-example --- still metadata\nBody",
                     "# Procedure\n---\nBody"):
            with self.subTest(text=text):
                self.assertEqual(GENERATOR.parse_frontmatter(text), ({}, text))
        self.assertEqual(GENERATOR.parse_frontmatter("---\nname: ia-example\n---"),
                         ({"name": "ia-example"}, ""))

    def test_cli_renders_metadata_and_preserves_existing_specs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copyfile(SCRIPT, root / SCRIPT.name)
            skills = root / "plugins/whetstone/skills"
            skill = skills / "ia-example"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: ia-example\ndescription: Inspect --- then validate.\n"
                "class: discipline\n---\n# Procedure\n", encoding="utf-8")
            fixtures = root / "distillery/tests/fixtures/triggers"
            fixtures.mkdir(parents=True)
            (fixtures / "ia-example.jsonl").write_text("\n".join(
                json.dumps(item) for item in [
                    {"prompt": "validate input", "expect": True},
                    {"prompt": "draw a picture", "expect": False},
                ]), encoding="utf-8")
            existing = skills / "ia-existing"
            existing.mkdir()
            (existing / "SKILL.md").write_text("# Existing", encoding="utf-8")
            sentinel = "Existing hand-maintained specification.\n"
            (existing / "SPEC.md").write_text(sentinel, encoding="utf-8")
            result = subprocess.run([sys.executable, SCRIPT.name], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = (skill / "SPEC.md").read_text(encoding="utf-8")
            self.assertIn("`ia-example` is a `discipline`-class skill", output)
            self.assertIn("Inspect --- then validate.", output)
            self.assertIn('  - "validate input"', output)
            self.assertIn('  - "draw a picture"', output)
            self.assertIn("Wrote 1 SPEC.md, skipped 1", result.stdout)
            self.assertEqual((existing / "SPEC.md").read_text(encoding="utf-8"), sentinel)


if __name__ == "__main__":
    unittest.main()
