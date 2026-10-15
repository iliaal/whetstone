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
