import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "openai_package", REPO_ROOT / "scripts/package-openai-plugin.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the OpenAI package builder")
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class OpenAIArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / "plugins/whetstone"
        self.write(
            "plugins/whetstone/.codex-plugin/plugin.json",
            json.dumps({
                "name": "whetstone", "version": "5.0.0",
                "description": "Engineering workflows",
                "author": {"name": "Publisher"},
                "mcpServers": "./.mcp.json", "apps": "./.app.json",
                "hooks": "./hooks/hooks.json", "commands": "./commands/",
                "agents": "./agents/",
            }),
        )
        self.write("plugins/whetstone/LICENSE", "MIT license")
        self.write("packaging/openai/interface.json", json.dumps({
            "displayName": "Whetstone", "shortDescription": "Engineering workflows",
            "logo": "./assets/whetstone.svg", "composerIcon": "./assets/whetstone.svg",
        }))
        self.write("packaging/openai/whetstone.svg", '<svg viewBox="0 0 512 512"/>')
        self.write("plugins/whetstone/skills/ia-demo/SKILL.md", "Run [helper](./scripts/helper.py).")
        self.write("plugins/whetstone/skills/ia-demo/scripts/helper.py", "print('unique helper')\n")
        self.write("plugins/whetstone/skills/ia-demo/SPEC.md", "Repository design notes")
        self.git("init", "-q")
        self.git("add", "plugins/whetstone/skills")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, timeout=30,
        )

    def test_archive_preserves_resources_and_excludes_integrations_and_untracked_files(self):
        secret = self.write("plugins/whetstone/skills/ia-demo/local-secret.txt", "private sentinel")
        before = (self.plugin / ".codex-plugin/plugin.json").read_bytes()
        output = self.root / "submission.zip"
        self.assertEqual(PACKAGE.build_archive(self.root, output), 1)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), {
                ".codex-plugin/plugin.json", "assets/whetstone.svg", "LICENSE",
                "skills/ia-demo/SKILL.md", "skills/ia-demo/scripts/helper.py",
            })
            manifest = json.loads(archive.read(".codex-plugin/plugin.json"))
            self.assertTrue({"mcpServers", "apps", "hooks", "commands", "agents"}.isdisjoint(manifest))
            self.assertEqual(archive.read("skills/ia-demo/scripts/helper.py"),
                             (self.plugin / "skills/ia-demo/scripts/helper.py").read_bytes())
            self.assertEqual(archive.read("assets/whetstone.svg"),
                             (self.root / "packaging/openai/whetstone.svg").read_bytes())
            self.assertIsNone(archive.testzip())
        self.assertEqual((self.plugin / ".codex-plugin/plugin.json").read_bytes(), before)
        self.assertEqual(secret.read_text(), "private sentinel")

    def test_existing_destination_is_preserved(self):
        output = self.write("submission.zip", "existing user artifact")
        with self.assertRaises(FileExistsError):
            PACKAGE.build_archive(self.root, output)
        self.assertEqual(output.read_text(), "existing user artifact")

    def test_same_inputs_produce_identical_archives(self):
        first, second = self.root / "first.zip", self.root / "second.zip"
        PACKAGE.build_archive(self.root, first)
        PACKAGE.build_archive(self.root, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_missing_tracked_resource_does_not_create_archive(self):
        (self.plugin / "skills/ia-demo/scripts/helper.py").unlink()
        output = self.root / "submission.zip"
        with self.assertRaisesRegex(ValueError, "regular file"):
            PACKAGE.build_archive(self.root, output)
        self.assertFalse(output.exists())

    def test_no_skills_does_not_create_archive(self):
        self.git("rm", "--cached", "-r", "plugins/whetstone/skills")
        output = self.root / "submission.zip"
        with self.assertRaisesRegex(ValueError, "no tracked skills"):
            PACKAGE.build_archive(self.root, output)
        self.assertFalse(output.exists())

    def test_invalid_listing_does_not_create_archive(self):
        self.write("packaging/openai/interface.json", json.dumps({"shortDescription": "x" * 31}))
        output = self.root / "submission.zip"
        with self.assertRaisesRegex(ValueError, "30 characters"):
            PACKAGE.build_archive(self.root, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
