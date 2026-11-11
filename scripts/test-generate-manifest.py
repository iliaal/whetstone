#!/usr/bin/env python3
"""Regression tests for trigger-history generation and eval staleness."""

import hashlib
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

    def generate(self, version, pattern=None, negative=None):
        self.plugin.write_text(json.dumps({"version": version}), encoding="utf-8")
        self.patterns.write_text(
            (f"SKILL_PATTERNS[ia-example]='{pattern}'\n" if pattern is not None else "")
            + (f"SKILL_NEGATIVE[ia-example]='{negative}'\n" if negative is not None else ""),
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

    def test_bundle_hashes_preserve_git_inventory_and_refresh_between_calls(self):
        self.plugin.write_text('{"version": "1.0.0"}', encoding="utf-8")
        (self.root / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
        expected = {}
        for name in ("ia-example", "ia-example-more", "ia-spaced name"):
            skill = self.skills / name
            skill.mkdir(exist_ok=True)
            files = {
                "SKILL.md": f"# {name}\n".encode(),
                "references/space name.md": b"reference\n",
                "assets/tab\tline\n\u00e9.bin": b"\x00\xffbinary",
                "tracked.ignored": b"tracked despite ignore rule\n",
                "untracked.txt": b"new reference\n",
            }
            for rel, data in files.items():
                target = skill / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            subprocess.run(
                ["git", "-C", str(self.root), "add", "-f", "--",
                 str(skill / "SKILL.md"), str(skill / "tracked.ignored")], check=True,
            )
            deleted = skill / "deleted.txt"
            deleted.write_text("deleted tracked file", encoding="utf-8")
            subprocess.run(["git", "-C", str(self.root), "add", "--", str(deleted)], check=True)
            deleted.unlink()
            (skill / "artifact.ignored").write_text("not published", encoding="utf-8")
            expected[name] = files

        # Files outside a direct skill directory must not enter another bundle.
        (self.skills / "README.md").write_text("skill index", encoding="utf-8")
        (self.skills / "no-skill").mkdir()
        (self.skills / "no-skill" / "reference.md").write_text("no SKILL.md", encoding="utf-8")
        (self.root / "unrelated.txt").write_text("outside skills", encoding="utf-8")

        def assert_bundles(manifest):
            self.assertEqual(set(manifest["skills"]), set(expected))
            for name, files in expected.items():
                digest = hashlib.sha256()
                for rel, data in sorted(files.items()):
                    encoded = rel.encode()
                    digest.update(len(encoded).to_bytes(8, "big") + encoded)
                    digest.update(len(data).to_bytes(8, "big") + data)
                self.assertEqual(manifest["skills"][name]["bundle_hash"], digest.hexdigest())

        initial = MANIFEST.generate()
        assert_bundles(initial)
        self.manifest.write_text(json.dumps(initial), encoding="utf-8")
        self.plugin.write_text('{"version": "2.0.0"}', encoding="utf-8")

        changed = self.skills / "ia-example"
        (changed / "new.md").write_bytes(b"new\n")
        expected["ia-example"]["new.md"] = b"new\n"
        (changed / "untracked.txt").unlink()
        del expected["ia-example"]["untracked.txt"]
        (changed / "references/space name.md").write_bytes(b"updated\n")
        expected["ia-example"]["references/space name.md"] = b"updated\n"
        # Ignore an existing untracked file; tracked ignored files remain included.
        (self.root / ".gitignore").write_text("*.ignored\nuntracked.txt\n", encoding="utf-8")
        for name in ("ia-example-more", "ia-spaced name"):
            del expected[name]["untracked.txt"]
        refreshed = MANIFEST.generate()
        assert_bundles(refreshed)
        for entry in refreshed["skills"].values():
            self.assertEqual(entry["bundle_changed"], "2.0.0")
            self.assertEqual(entry["content_changed"], "1.0.0")

        self.manifest.write_text(json.dumps(refreshed), encoding="utf-8")
        self.plugin.write_text('{"version": "3.0.0"}', encoding="utf-8")
        unchanged = MANIFEST.generate()
        assert_bundles(unchanged)
        self.assertEqual(unchanged["skills"], refreshed["skills"])

    def test_generation_inventories_skills_once_per_call(self):
        for name in ("ia-second", "ia-third"):
            skill = self.skills / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        with patch.object(MANIFEST.subprocess, "run", autospec=True, side_effect=subprocess.run) as run:
            self.generate("1.0.0")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][-1], "skills")
            self.generate("2.0.0")
            self.assertEqual(run.call_count, 2)

    def test_empty_skill_inventory_does_not_require_git(self):
        (self.skills / "ia-example" / "SKILL.md").unlink()
        with patch.object(MANIFEST.subprocess, "run", autospec=True, side_effect=subprocess.run) as run:
            self.assertEqual(self.generate("1.0.0")["skills"], {})
            run.assert_not_called()

    def test_ignored_bundle_keeps_empty_hash_without_another_git_call(self):
        (self.root / ".gitignore").write_text("skills/\n", encoding="utf-8")
        with patch.object(MANIFEST.subprocess, "run", autospec=True, side_effect=subprocess.run) as run:
            entry = self.generate("1.0.0")["skills"]["ia-example"]
            self.assertEqual(entry["bundle_hash"], hashlib.sha256().hexdigest())
            self.assertEqual(run.call_count, 1)

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

    def test_commenting_assignment_records_trigger_change(self):
        for quote in ("'", '"'):
            for prefix in ("# ", " \t# "):
                for array in ("SKILL_PATTERNS", "SKILL_NEGATIVE"):
                    with self.subTest(quote=quote, prefix=prefix, array=array):
                        self.manifest.unlink(missing_ok=True)
                        initial = self.generate("1.0.0", "review", "blocked")
                        self.plugin.write_text('{"version": "2.0.0"}', encoding="utf-8")
                        active = (f"SKILL_PATTERNS[ia-example]={quote}review{quote}\n"
                                  f"SKILL_NEGATIVE[ia-example]={quote}blocked{quote}\n")
                        commented = active.replace(array + "[", prefix + array + "[")
                        self.patterns.write_text(commented, encoding="utf-8")
                        changed = MANIFEST.generate()
                        entry = changed["skills"]["ia-example"]
                        self.assertNotEqual(entry.get("pattern_hash"),
                                            initial["skills"]["ia-example"]["pattern_hash"])
                        self.assertEqual(entry["pattern_changed"], "2.0.0")
                        self.assert_staleness(changed, "1.0.0", True)
                        self.assert_staleness(changed, "2.0.0", False)
                        if array == "SKILL_PATTERNS":
                            self.assertNotIn("pattern_hash", entry)
                        else:
                            self.assertEqual(entry["pattern_hash"], MANIFEST._sha256_string("review"))

    def test_comments_do_not_shadow_indented_active_assignments(self):
        for quote in ("'", '"'):
            with self.subTest(quote=quote):
                content = (
                    "# SKILL_PATTERNS[ia-example]='old'\n"
                    "# SKILL_NEGATIVE[ia-example]='old-negative'\n"
                    f" \tSKILL_PATTERNS[ia-example]={quote}review#tag  code{quote} # comment\n"
                    f" \tSKILL_NEGATIVE[ia-example]={quote}skip#tag{quote} # comment\n"
                    '# SKILL_PATTERNS[ia-example]="later"\n'
                    '# SKILL_NEGATIVE[ia-example]="later-negative"\n'
                )
                self.assertEqual(MANIFEST._extract_pattern_block("ia-example", content),
                                 "review#tag  code\x00!skip#tag")

    def test_significant_regex_whitespace_invalidates_older_examples(self):
        cases = (
            ("review code", "review  code", "review code"),
            ("review code", "review\tcode", "review code"),
            ("review code", " review code", "review code"),
            ("review code", "review code ", "review code"),
            ("review[ ]code", "review[\t]code", "review code"),
        )
        for negative in (False, True):
            for before, after, prompt in cases:
                with self.subTest(negative=negative, before=before, after=after):
                    self.manifest.unlink(missing_ok=True)
                    # Exercise the same ERE matcher used by the injection hook.
                    for pattern, expected in ((before, 0), (after, 1)):
                        matched = subprocess.run(
                            ["grep", "-Eq", "--", pattern], input=prompt + "\n",
                            text=True, capture_output=True, check=False,
                        )
                        self.assertEqual(matched.returncode, expected, matched.stderr)

                    def generate(version, expression, negative=negative):
                        return self.generate(
                            version, "review" if negative else expression,
                            expression if negative else None,
                        )

                    initial = generate("1.0.0", before)
                    changed = generate("2.0.0", after)
                    entry = changed["skills"]["ia-example"]
                    self.assertNotEqual(entry["pattern_hash"], initial["skills"]["ia-example"]["pattern_hash"])
                    self.assertEqual(entry["pattern_changed"], "2.0.0")
                    self.assert_staleness(changed, "1.0.0", True)
                    self.assert_staleness(changed, "2.0.0", False)
                    unchanged = generate("3.0.0", after)
                    self.assertEqual(unchanged["skills"]["ia-example"]["pattern_changed"], "2.0.0")
                    self.assert_staleness(unchanged, "2.0.0", False)


if __name__ == "__main__":
    unittest.main()
