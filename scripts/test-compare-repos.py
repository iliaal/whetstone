#!/usr/bin/env python3
"""Regression tests for comparison CLI repository discovery (stdlib only)."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("compare-repos.py")


class RepositoryDiscoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checkout = self.root / "whetstone"
        self.script = self.checkout / "scripts" / SCRIPT.name
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.script)
        self.write(self.checkout, "plugins/whetstone/agents/ia-local.md", "# Local\n")

    def write(self, root, relative, text="---\ndescription: Review changes.\n---\n# Review\n"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(self.script), *map(str, args)], cwd=self.root,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def make_agents_repo(self, name="agent-only", *, versioned=True):
        repo = self.root / name
        self.write(repo, "agents/reviewer.md")
        self.write(repo, "agents/quality/tester.md")
        if versioned:
            (repo / ".git").mkdir()
        return repo

    def test_direct_agents_repository_is_cataloged(self):
        repo = self.make_agents_repo()
        result = self.run_cli("--catalog", repo)
        self.assertIn("[A] agent-only/reviewer (4 lines)", result.stdout)
        self.assertIn("[A] agent-only/tester (4 lines)", result.stdout)
        catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
        self.assertEqual(
            {(c["repo"], c["kind"], c["path"]) for c in catalog},
            {("agent-only", "agent", "agents/reviewer.md"),
             ("agent-only", "agent", "agents/quality/tester.md")},
        )

    def test_direct_agents_repository_appears_in_report(self):
        repo = self.make_agents_repo()
        output = self.root / "comparison.md"
        result = self.run_cli("--type", "agents", "--output", output, repo)
        report = output.read_text(encoding="utf-8")
        self.assertIn("- **agent-only**: 0 skills, 2 agents", report)
        self.assertIn("| agent | reviewer | 4 | Review changes. |", report)
        self.assertIn("| agent | tester | 4 | Review changes. |", report)
        self.assertIn("External: 0 skills, 2 agents", result.stdout)

    def test_direct_repository_with_only_nested_agents_is_cataloged(self):
        repo = self.root / "nested-agents"
        self.write(repo, "agents/quality/reviewer.md")
        (repo / ".git").mkdir()
        result = self.run_cli("--catalog", repo)
        self.assertIn("[A] nested-agents/reviewer (4 lines)", result.stdout)

    def test_direct_agents_worktree_is_cataloged(self):
        repo = self.make_agents_repo(versioned=False)
        self.write(repo, ".git", "gitdir: ../main/.git/worktrees/agent-only\n")
        result = self.run_cli("--catalog", repo)
        self.assertIn("[A] agent-only/reviewer (4 lines)", result.stdout)
        self.assertIn("[A] agent-only/tester (4 lines)", result.stdout)

    def test_parent_directory_keeps_discovering_repositories(self):
        parent = self.root / "repos"
        agents = self.make_agents_repo("repos/agents")
        skills = parent / "skills-only"
        self.write(skills, "skills/build/SKILL.md")
        for repo in (agents, skills):
            (repo / ".git").mkdir(exist_ok=True)
        result = self.run_cli("--catalog", parent)
        self.assertIn("[A] agents/reviewer (4 lines)", result.stdout)
        self.assertIn("[A] agents/tester (4 lines)", result.stdout)
        self.assertIn("[S] skills-only/build (4 lines)", result.stdout)

    def test_archive_parent_keeps_agents_and_sibling_repository(self):
        parent = self.root / "archives"
        self.make_agents_repo("archives/agents", versioned=False)
        self.write(parent, "skills-only/skills/build/SKILL.md")
        result = self.run_cli("--catalog", parent)
        self.assertIn("[A] agents/reviewer (4 lines)", result.stdout)
        self.assertIn("[A] agents/tester (4 lines)", result.stdout)
        self.assertIn("[S] skills-only/build (4 lines)", result.stdout)
        catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
        self.assertEqual(
            {(c["repo"], c["kind"], c["path"]) for c in catalog},
            {("agents", "agent", "agents/reviewer.md"),
             ("agents", "agent", "agents/quality/tester.md"),
             ("skills-only", "skill", "skills/build/SKILL.md")},
        )

    def test_existing_single_repository_layouts_are_cataloged(self):
        for name, relative, expected in (
            ("skills-only", "skills/build/SKILL.md", "[S] skills-only/build"),
            ("categorized", "categories/quality/reviewer.md", "[A] categorized/quality/reviewer"),
            ("plugin", "plugins/example/agents/reviewer.md", "[A] plugin/example/reviewer"),
        ):
            with self.subTest(layout=name):
                repo = self.root / name
                self.write(repo, relative)
                if name == "plugin":
                    self.write(repo, "plugins/example/.claude-plugin/plugin.json", "{}\n")
                self.assertIn(expected + " (4 lines)", self.run_cli("--catalog", repo).stdout)

    def test_empty_agents_directory_does_not_hide_child_repositories(self):
        parent = self.root / "repos"
        (parent / "agents").mkdir(parents=True)
        (parent / ".git").mkdir()
        self.write(parent, "skills-only/skills/build/SKILL.md")
        result = self.run_cli("--catalog", parent)
        self.assertIn("[S] skills-only/build (4 lines)", result.stdout)

    def test_non_agent_entries_do_not_hide_child_repositories(self):
        parent = self.root / "repos"
        (parent / "agents/folder.md").mkdir(parents=True)
        (parent / ".git").mkdir()
        self.write(parent, "agents/notes.txt", "Notes\n")
        self.write(parent, "skills-only/skills/build/SKILL.md")
        result = self.run_cli("--catalog", parent)
        self.assertIn("[S] skills-only/build (4 lines)", result.stdout)


if __name__ == "__main__":
    unittest.main()
