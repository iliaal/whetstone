#!/usr/bin/env python3
"""Regression tests for trigger-history generation and eval staleness."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("generate_manifest", ROOT / "scripts/generate-manifest.py")
MANIFEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANIFEST)
sys.path.insert(0, str(ROOT / "distillery/scripts"))
import distiller


class TriggerHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skills = self.root / "skills"
        skill = self.skills / "ia-example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Example\n", encoding="utf-8")
        self.patterns = self.root / "patterns.sh"
        self.patterns.write_text("", encoding="utf-8")
        self.plugin = self.root / "plugin.json"
        self.manifest = self.root / "manifest.json"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        replacements = {
            "REPO_ROOT": self.root, "SKILLS_DIR": self.skills,
            "PATTERNS_FILE": self.patterns, "PLUGIN_JSON": self.plugin,
            "MANIFEST_PATH": self.manifest,
        }
        for name, value in replacements.items():
            patcher = patch.object(MANIFEST, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def generate(self, version, pattern=None):
        self.plugin.write_text(json.dumps({"version": version}), encoding="utf-8")
        self.patterns.write_text(
            f"SKILL_PATTERNS[ia-example]='{pattern}'\n" if pattern is not None else "",
            encoding="utf-8",
        )
        manifest = MANIFEST.generate()
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def assert_staleness(self, manifest, version, pattern_stale):
        self.assertEqual(
            distiller._is_example_stale({"skill_version": version}, "ia-example", manifest),
            {"content_stale": False, "pattern_stale": pattern_stale, "model_stale": False},
        )

    def test_removal_records_change_and_keeps_older_examples_stale(self):
        self.generate("1.0.0", "example")
        removed = self.generate("2.0.0")
        self.assert_staleness(removed, "1.0.0", True)
        entry = removed["skills"]["ia-example"]
        self.assertNotIn("pattern_hash", entry)
        self.assertEqual(entry["pattern_changed"], "2.0.0")
        self.assert_staleness(removed, "2.0.0", False)

    def test_continued_absence_preserves_removal_version(self):
        self.generate("1.0.0", "example")
        self.generate("2.0.0")
        absent = self.generate("3.0.0")
        self.assert_staleness(absent, "1.0.0", True)
        self.assertNotIn("pattern_hash", absent["skills"]["ia-example"])
        self.assertEqual(absent["skills"]["ia-example"]["pattern_changed"], "2.0.0")
        self.assert_staleness(absent, "2.0.0", False)

    def test_never_configured_skill_keeps_pattern_fields_absent(self):
        for version in ("1.0.0", "2.0.0"):
            with self.subTest(version=version):
                manifest = self.generate(version)
                entry = manifest["skills"]["ia-example"]
                self.assertNotIn("pattern_hash", entry)
                self.assertNotIn("pattern_changed", entry)
                self.assert_staleness(manifest, "1.0.0", False)

    def test_restored_and_unchanged_trigger_versions(self):
        initial = self.generate("1.0.0", "example")
        self.generate("2.0.0")
        restored = self.generate("3.0.0", "example")
        entry = restored["skills"]["ia-example"]
        self.assertEqual(entry["pattern_hash"], initial["skills"]["ia-example"]["pattern_hash"])
        self.assertEqual(entry["pattern_changed"], "3.0.0")
        self.assert_staleness(restored, "2.0.0", True)
        self.assert_staleness(restored, "3.0.0", False)
        unchanged = self.generate("4.0.0", "example")
        self.assertEqual(unchanged["skills"]["ia-example"]["pattern_changed"], "3.0.0")


if __name__ == "__main__":
    unittest.main()
