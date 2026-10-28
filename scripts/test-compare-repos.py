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

    def test_nonfinite_thresholds_fail_before_scanning_or_writing(self):
        repo = self.make_agents_repo()
        output = self.root / "comparison.md"
        self.write(self.checkout, ".compare-cache/ours.json", "ours sentinel\n")
        self.write(self.checkout, ".compare-cache/external.json", "external sentinel\n")
        output.write_text("report sentinel\n", encoding="utf-8")
        tracked = [output, *sorted((self.checkout / ".compare-cache").iterdir())]
        before = {path: path.read_bytes() for path in tracked}
        for value in ("nan", "NaN", "+nan", "-nan", "inf", "+inf", "-inf",
                      "Infinity", "-Infinity", "1e999", "-1e999"):
            for mode in ((str(repo),), ("--report-only",), ("--catalog", str(repo))):
                with self.subTest(value=value, mode=mode):
                    result = subprocess.run(
                        [sys.executable, str(self.script), f"--threshold={value}",
                         "--output", str(output), *mode], cwd=self.root,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("--threshold must be finite", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Scanning", result.stderr)
                    self.assertEqual({path: path.read_bytes() for path in tracked}, before)

    def test_finite_thresholds_keep_existing_matching_semantics(self):
        self.write(self.checkout, "plugins/whetstone/agents/ia-review.md", "# Review\n")
        repo = self.root / "matching"
        self.write(repo, "agents/review.md", "# Review\n")
        (repo / ".git").mkdir()
        output = self.root / "comparison.md"
        for value, count in (("-1", 2), ("0", 2), ("0.15", 1), ("0.9999999999999999", 1),
                             ("1", 1), ("1.0000000000000002", 0), ("2", 0)):
            for mode in ((repo,), ("--report-only",)):
                with self.subTest(value=value, mode=mode):
                    result = self.run_cli(f"--threshold={value}", "--output", output, *mode)
                    self.assertIn(f"Overlaps: {count} total", result.stdout)

    def test_same_name_of_different_kind_is_reported_as_gap(self):
        for local_kind, external_kind in (("skills", "agents"), ("agents", "skills")):
            with self.subTest(local_kind=local_kind):
                name = "alpha" if local_kind == "skills" else "bravo"
                local_file = f"{name}/SKILL.md" if local_kind == "skills" else f"{name}.md"
                external_file = f"{name}/SKILL.md" if external_kind == "skills" else f"{name}.md"
                self.write(self.checkout, f"plugins/whetstone/{local_kind}/ia-{local_file}")
                repo = self.root / name
                self.write(repo, f"{external_kind}/{external_file}")
                (repo / ".git").mkdir()
                output = self.root / f"{name}.md"
                for args in ((repo,), ("--report-only",)):
                    result = self.run_cli("--type", external_kind, "--output", output, *args)
                    report = output.read_text(encoding="utf-8")
                    self.assertIn(f"| {external_kind[:-1]} | {name} |", report)
                    self.assertIn("Gaps: 1 unmatched external components", result.stdout)

    def test_same_kind_prefixed_name_is_not_reported_as_gap(self):
        for kind in ("skills", "agents"):
            with self.subTest(kind=kind):
                name = "same-" + kind
                relative = f"{name}/SKILL.md" if kind == "skills" else f"{name}.md"
                self.write(self.checkout, f"plugins/whetstone/{kind}/ia-{relative}")
                repo = self.root / name
                self.write(repo, f"{kind}/{relative}")
                (repo / ".git").mkdir()
                output = self.root / f"{name}.md"
                result = self.run_cli("--type", kind, "--output", output, repo)
                self.assertIn("Gaps: 0 unmatched external components", result.stdout)
                self.assertIn(f"| ia-{name} | {name} |", output.read_text(encoding="utf-8"))

    def test_distinct_same_name_overlaps_survive_report_deduplication(self):
        layouts = (
            ("cross-kind", ("skills/ia-review/SKILL.md", "agents/ia-review.md"),
             ("skills/review/SKILL.md", "agents/review.md"), 2),
            ("external-paths", ("agents/ia-review.md",),
             ("agents/quality/review.md", "agents/security/review.md"), 2),
            ("local-paths", ("agents/quality/ia-review.md", "agents/security/ia-review.md"),
             ("agents/review.md",), 2),
        )
        for name, local_paths, external_paths, expected_count in layouts:
            with self.subTest(layout=name):
                # Isolate each layout while retaining the CLI's real scanner.
                plugin = self.checkout / "plugins/whetstone"
                shutil.rmtree(plugin)
                repo = self.root / name
                (repo / ".git").mkdir(parents=True)
                for index, relative in enumerate(local_paths):
                    self.write(plugin, relative, "# Review\n" * (index + 2))
                for index, relative in enumerate(external_paths):
                    self.write(repo, relative, "# Review\n" * (index + 4))
                output = self.root / f"{name}.md"
                for args in ((repo,), ("--report-only",)):
                    self.run_cli("--output", output, *args)
                    report = output.read_text(encoding="utf-8")
                    table = report.split("## Overlapping Components", 1)[1].split(
                        "### High-Similarity", 1)[0]
                    rows = [line for line in table.splitlines()
                            if line.startswith("| ia-review | review |")]
                    self.assertEqual(len(rows), expected_count, report)
                    self.assertEqual(len(set(rows)), expected_count, report)
                    self.assertIn(f"## Overlapping Components ({expected_count} matches)", report)
                    self.assertIn(f"- Overlapping matches: {expected_count}", report)

    def test_repeated_repository_keeps_report_match_counts_consistent(self):
        self.write(self.checkout, "plugins/whetstone/agents/ia-review.md", "# Review\n")
        repo = self.root / "repeated"
        self.write(repo, "agents/review.md", "# Review\n")
        (repo / ".git").mkdir()
        output = self.root / "repeated.md"
        for args in ((repo, repo), ("--report-only",)):
            self.run_cli("--output", output, *args)
            report = output.read_text(encoding="utf-8")
            self.assertIn("## Overlapping Components (1 matches)", report)
            self.assertIn("- Overlapping matches: 1", report)
            self.assertIn("- High-similarity (>=0.50): 1", report)
            self.assertEqual(report.count("| ia-review | review |"), 1)
            self.assertEqual(report.count("- **ia-review** vs **review**"), 1)

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
