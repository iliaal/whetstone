#!/usr/bin/env python3
"""Regression tests for comparison CLI discovery and filtering (stdlib only)."""

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

    def test_folded_descriptions_survive_scanning_cache_and_report(self):
        description = "Review changes: inspect code. description: keep this text."
        repo = self.root / "folded"
        for marker in (">", ">-", ">+", ">- # folded description"):
            for newline in ("\n", "\r\n"):
                with self.subTest(marker=marker, newline=repr(newline)):
                    content = newline.join([
                        "---", "name: review", f"description: {marker}",
                        "  Review changes: inspect code.",
                        "  description: keep this text.", "class: discipline",
                        "---", "# Review", "",
                    ])
                    self.write(repo, "skills/review/SKILL.md", content)
                    self.write(repo, "agents/review.md", content)
                    for args in ((repo,), ("--report-only",)):
                        result = self.run_cli("--catalog", *args)
                        self.assertEqual(result.stdout.count("    " + description + "\n"), 2)
                        cache = self.checkout / ".compare-cache/external.json"
                        self.assertEqual([c["description"] for c in json.loads(cache.read_text())],
                                         [description, description])
                        output = self.root / "folded.md"
                        self.run_cli("--output", output, *args)
                        self.assertEqual(output.read_text().count(description), 2)

    def test_folded_descriptions_stop_at_same_indentation(self):
        repo = self.root / "indented"
        for body, expected in (("    First paragraph.\n\n    Second paragraph.\n",
                                "First paragraph. Second paragraph."), ("", "")):
            with self.subTest(body=body):
                self.write(repo, "skills/review/SKILL.md",
                           "---\n  description: >-\n" + body
                           + "  name: review\n---\n# Review\n")
                self.run_cli("--catalog", repo)
                cache = self.checkout / ".compare-cache/external.json"
                self.assertEqual(json.loads(cache.read_text())[0]["description"], expected)

    def test_inline_descriptions_keep_existing_catalog_text(self):
        repo = self.root / "inline"
        for value, expected in (("Review changes.", "Review changes."),
                                ('"Review: changes."', "Review: changes."),
                                ("'>'", ">"), ('">-"', ">-")):
            with self.subTest(value=value):
                self.write(repo, "skills/review/SKILL.md",
                           f"---\ndescription: {value}\nname: review\n---\n# Review\n")
                result = self.run_cli("--catalog", repo)
                self.assertIn("    " + expected + "\n", result.stdout)

    def test_catalog_type_filters_display_without_narrowing_cache(self):
        repo = self.root / "mixed"
        self.write(repo, "skills/build/SKILL.md", "# Build\n")
        self.write(repo, "agents/reviewer.md", "# Review\n")
        agent = "[A] mixed/reviewer (1 lines)\n"
        skill = "[S] mixed/build (1 lines)\n"
        for kind, expected in (("skills", skill), ("agents", agent), (None, agent + skill)):
            for mode in ((repo,), ("--report-only",)):
                with self.subTest(kind=kind, mode=mode):
                    options = ("--type", kind) if kind else ()
                    result = self.run_cli("--catalog", *options, *mode)
                    self.assertEqual(result.stdout, expected)
                    cache = self.checkout / ".compare-cache/external.json"
                    self.assertEqual({c["kind"] for c in json.loads(cache.read_text())},
                                     {"skill", "agent"})

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

    def test_duplicate_repository_paths_are_scanned_once(self):
        parent = self.root / "repos"
        repo = self.make_agents_repo("repos/agent-only")
        alias = self.root / "alias"
        alias.symlink_to(repo, target_is_directory=True)
        (parent / "linked").symlink_to(repo, target_is_directory=True)
        output = self.root / "comparison.md"
        for paths in ((repo, repo), (repo, alias), (parent, repo)):
            with self.subTest(paths=paths):
                result = self.run_cli("--output", output, *paths)
                self.assertEqual(result.stderr.count("Scanning agent-only..."), 1)
                self.assertIn("External: 0 skills, 2 agents", result.stdout)
                self.assertIn("Gaps: 2 unmatched external components", result.stdout)
                cache = self.checkout / ".compare-cache/external.json"
                self.assertEqual(len(json.loads(cache.read_text())), 2)
                for mode in (("--report-only",), paths):
                    catalog = self.run_cli("--catalog", *mode)
                    self.assertEqual(catalog.stdout.count("[A] agent-only/reviewer"), 1)
                    self.assertEqual(catalog.stdout.count("[A] agent-only/tester"), 1)
                report = self.run_cli("--report-only", "--output", output)
                self.assertIn("Gaps: 2 unmatched external components", report.stdout)
                self.assertIn("## Unmatched External Components (2 items)",
                              output.read_text())

    def test_distinct_repositories_with_same_name_are_not_deduplicated(self):
        first = self.make_agents_repo("first/shared")
        second = self.make_agents_repo("second/shared")
        result = self.run_cli("--catalog", first, second)
        self.assertEqual(result.stdout.count("[A] shared/reviewer"), 2)
        self.assertEqual(result.stdout.count("[A] shared/tester"), 2)
        cache = self.checkout / ".compare-cache/external.json"
        self.assertEqual(len(json.loads(cache.read_text())), 4)

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

    def test_direct_agent_archives_survive_catalog_cache_and_report(self):
        for name, paths in (
            ("archive", ("agents/reviewer.md", "agents/quality/tester.md")),
            ("nested-archive", ("agents/quality/reviewer.md",)),
        ):
            with self.subTest(layout=name):
                repo = self.root / name
                for path in paths:
                    self.write(repo, path)
                expected = {(name, "agent", path) for path in paths}
                output = self.root / f"{name}.md"
                for args in ((repo,), ("--report-only",)):
                    self.run_cli("--catalog", *args)
                    catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
                    self.assertEqual({(c["repo"], c["kind"], c["path"]) for c in catalog}, expected)
                    result = self.run_cli("--type", "agents", "--output", output, *args)
                    self.assertIn(f"External: 0 skills, {len(paths)} agents", result.stdout)
                    self.assertIn(f"- **{name}**: 0 skills, {len(paths)} agents", output.read_text())

    def test_versioned_repository_keeps_agents_named_subgroup(self):
        for marker in ("directory", "file"):
            with self.subTest(marker=marker):
                repo = self.root / marker
                self.write(repo, "agents/agents/reviewer.md")
                if marker == "directory":
                    (repo / ".git").mkdir()
                else:
                    self.write(repo, ".git", "gitdir: ../main/.git/worktrees/agents\n")
                result = self.run_cli("--catalog", repo)
                self.assertEqual(result.stdout, f"[A] {marker}/reviewer (4 lines)\n    Review changes.\n")

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

    def test_archive_parent_with_repository_named_agents_uses_child_layout(self):
        for layout, path, expected in (
            ("agents", "agents/quality/reviewer.md", "[A] agents/reviewer"),
            ("skills", "skills/build/SKILL.md", "[S] agents/build"),
            ("plugin", "plugins/example/agents/reviewer.md", "[A] agents/example/reviewer"),
            ("categories", "categories/quality/reviewer.md", "[A] agents/quality/reviewer"),
        ):
            with self.subTest(layout=layout):
                parent = self.root / layout
                self.write(parent / "agents", path)
                if layout == "plugin":
                    self.write(parent / "agents", "plugins/example/.claude-plugin/plugin.json", "{}\n")
                for sibling in (False, True):
                    with self.subTest(sibling=sibling):
                        if sibling:
                            self.write(parent, "other/skills/build/SKILL.md")
                        result = self.run_cli("--catalog", parent)
                        entries = [line for line in result.stdout.splitlines() if line.startswith("[")]
                        wanted = [expected + " (4 lines)"]
                        if sibling:
                            wanted.append("[S] other/build (4 lines)")
                        self.assertEqual(entries, wanted)

    def test_empty_agents_directory_does_not_hide_child_repositories(self):
        parent = self.root / "repos"
        (parent / "agents").mkdir(parents=True)
        (parent / ".git").mkdir()
        self.write(parent, "skills-only/skills/build/SKILL.md")
        result = self.run_cli("--catalog", parent)
        self.assertIn("[S] skills-only/build (4 lines)", result.stdout)

    def test_mixed_archive_collection_does_not_catalog_repository_readme_as_agent(self):
        for marker in ("archive", "directory", "file"):
            with self.subTest(marker=marker):
                parent = self.root / marker
                self.write(parent, "agents/README.md", "# Unsupported repository\n")
                self.write(parent, "skills-only/skills/build/SKILL.md")
                if marker == "directory":
                    (parent / "agents/.git").mkdir()
                elif marker == "file":
                    self.write(parent, "agents/.git", "gitdir: ../../main/.git/worktrees/agents\n")
                output = self.root / f"{marker}.md"
                for args in ((parent,), ("--report-only",)):
                    result = self.run_cli("--catalog", *args)
                    self.assertEqual(result.stdout, "[S] skills-only/build (4 lines)\n    Review changes.\n")
                    catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
                    self.assertEqual(
                        {(c["repo"], c["kind"], c["path"]) for c in catalog},
                        {("skills-only", "skill", "skills/build/SKILL.md")},
                    )
                    result = self.run_cli("--output", output, *args)
                    report = output.read_text()
                    self.assertIn("External: 1 skills, 0 agents", result.stdout)
                    self.assertIn("- **skills-only**: 1 skills, 0 agents", report)
                    self.assertNotIn("| agent | README |", report)
                    if args == (parent,):
                        self.assertIn("layout not recognized", report)

    def test_agent_only_archive_discovery_respects_sibling_repository_layouts(self):
        for layout, path, expected in (
            ("agents", "agents/reviewer.md", "[A] other/reviewer"),
            ("skills", "skills/build/SKILL.md", "[S] other/build"),
            ("plugin", "plugins/example/agents/reviewer.md", "[A] other/example/reviewer"),
            ("categories", "categories/quality/reviewer.md", "[A] other/quality/reviewer"),
        ):
            with self.subTest(layout=layout):
                parent = self.root / layout
                self.write(parent, "agents/README.md", "# Unsupported repository\n")
                self.write(parent / "other", path)
                if layout == "plugin":
                    self.write(parent / "other", "plugins/example/.claude-plugin/plugin.json", "{}\n")
                self.assertEqual(self.run_cli("--catalog", parent).stdout,
                                 expected + " (4 lines)\n    Review changes.\n")

    def test_direct_repository_git_marker_overrides_sibling_layout_hint(self):
        for marker in ("directory", "file"):
            with self.subTest(marker=marker):
                repo = self.root / marker
                self.write(repo, "agents/README.md")
                self.write(repo, "examples/skills/build/SKILL.md")
                if marker == "directory":
                    (repo / ".git").mkdir()
                else:
                    self.write(repo, ".git", "gitdir: ../main/.git/worktrees/example\n")
                self.assertEqual(self.run_cli("--catalog", repo).stdout,
                                 f"[A] {marker}/README (4 lines)\n    Review changes.\n")

    def test_direct_agent_archive_keeps_agents_with_bundled_example_repository(self):
        repo = self.root / "archive"
        self.write(repo, "agents/quality/reviewer.md")
        self.write(repo, "agents/README.md", "# Agents\n")
        self.write(repo, "examples/skills/build/SKILL.md")
        self.assertEqual(self.run_cli("--catalog", repo).stdout,
                         "[A] archive/README (1 lines)\n"
                         "[A] archive/reviewer (4 lines)\n    Review changes.\n"
                         "[S] examples/build (4 lines)\n    Review changes.\n")

    def test_real_parent_agents_keep_each_supported_sibling_layout(self):
        for layout, path, sibling_repo, kind, name in (
            ("agents", "agents/tester.md", "other", "agent", "tester"),
            ("skills", "skills/build/SKILL.md", "other", "skill", "build"),
            ("plugin", "plugins/example/agents/tester.md", "other/example", "agent", "tester"),
            ("categories", "categories/quality/tester.md", "other/quality", "agent", "tester"),
        ):
            for marker in ("archive", "directory", "file"):
                with self.subTest(layout=layout, marker=marker):
                    parent = self.root / f"{layout}-{marker}"
                    self.write(parent, "agents/flat.md")
                    self.write(parent / "other", path)
                    if layout == "plugin":
                        self.write(parent / "other", "plugins/example/.claude-plugin/plugin.json", "{}\n")
                    if marker == "directory":
                        (parent / "other/.git").mkdir()
                    elif marker == "file":
                        self.write(parent, "other/.git", "gitdir: ../../main/.git/worktrees/other\n")
                    expected = {(parent.name, "agent", "flat"), (sibling_repo, kind, name)}
                    output = self.root / "mixed.md"
                    for args in ((parent,), ("--report-only",)):
                        self.run_cli("--catalog", *args)
                        catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
                        self.assertEqual({(c["repo"], c["kind"], c["name"]) for c in catalog}, expected)
                        result = self.run_cli("--output", output, *args)
                        skills = int(kind == "skill")
                        self.assertIn(f"External: {skills} skills, {2 - skills} agents", result.stdout)
                        report = output.read_text()
                        self.assertIn(f"- **{parent.name}**: 0 skills, 1 agents", report)
                        self.assertIn(f"- **other**: {skills} skills, {1 - skills} agents", report)

    def test_ambiguous_archive_siblings_are_filtered_and_deduplicated(self):
        parent = self.root / "archive"
        self.write(parent, "agents/flat.md")
        self.write(parent, "other/skills/build/SKILL.md")
        self.write(parent, ".hidden/skills/private/SKILL.md")
        self.write(parent, "unsupported/README.md")
        (parent / "linked").symlink_to(parent / "other", target_is_directory=True)
        result = self.run_cli("--catalog", "--type", "skills", parent, parent / "other")
        self.assertEqual(result.stdout, "[S] linked/build (4 lines)\n    Review changes.\n")
        catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
        self.assertEqual({(c["kind"], c["name"]) for c in catalog},
                         {("agent", "flat"), ("skill", "build")})
        self.assertEqual(len(catalog), 2)
        self.assertEqual(self.run_cli("--catalog", "--type", "agents", "--report-only").stdout,
                         "[A] archive/flat (4 lines)\n    Review changes.\n")

    def test_versioned_parent_real_agents_do_not_scan_bundled_sibling_layouts(self):
        for marker in ("directory", "file"):
            with self.subTest(marker=marker):
                parent = self.root / marker
                self.write(parent, "agents/flat.md")
                self.write(parent, "other/skills/build/SKILL.md")
                if marker == "directory":
                    (parent / ".git").mkdir()
                else:
                    self.write(parent, ".git", "gitdir: ../main/.git/worktrees/parent\n")
                self.assertEqual(self.run_cli("--catalog", parent).stdout,
                                 f"[A] {marker}/flat (4 lines)\n    Review changes.\n")

    def test_parent_non_agent_layout_keeps_direct_repository_interpretation(self):
        for layout, path, expected in (
            ("skills", "skills/build/SKILL.md", {("archive", "skill", "build")}),
            ("plugin", "plugins/example/agents/tester.md", {("archive/example", "agent", "tester")}),
            ("categories", "categories/agents/tester.md", {("archive/agents", "agent", "tester")}),
            ("manifest", ".claude-plugin/plugin.json", set()),
        ):
            with self.subTest(layout=layout):
                parent = self.root / layout / "archive"
                self.write(parent, "agents/flat.md")
                self.write(parent, path)
                if layout == "plugin":
                    self.write(parent, "plugins/example/.claude-plugin/plugin.json", "{}\n")
                self.write(parent, "other/skills/example/SKILL.md")
                for args in ((parent,), ("--report-only",)):
                    self.run_cli("--catalog", *args)
                    catalog = json.loads((self.checkout / ".compare-cache/external.json").read_text())
                    self.assertEqual({(c["repo"], c["kind"], c["name"]) for c in catalog},
                                     expected | {("archive", "agent", "flat")})
                    self.assertEqual(len(catalog), len(expected) + 1)

    def test_child_git_marker_identifies_unsupported_repository_without_siblings(self):
        for marker in ("directory", "file"):
            with self.subTest(marker=marker):
                parent = self.root / marker
                self.write(parent, "agents/README.md", "# Unsupported repository\n")
                self.write(parent, "agents/reviewer.md")
                if marker == "directory":
                    (parent / "agents/.git").mkdir()
                else:
                    self.write(parent, "agents/.git", "gitdir: ../../main/.git/worktrees/agents\n")
                self.assertEqual(self.run_cli("--catalog", parent).stdout, "")
                output = self.root / f"{marker}.md"
                result = self.run_cli("--output", output, parent)
                self.assertIn("External: 0 skills, 0 agents", result.stdout)
                self.assertIn("- **agents**: 0 components (layout not recognized)", output.read_text())

    def test_hidden_sibling_layout_does_not_hide_direct_agent_archive(self):
        repo = self.root / "archive"
        self.write(repo, "agents/README.md")
        self.write(repo, ".examples/skills/build/SKILL.md")
        self.assertEqual(self.run_cli("--catalog", repo).stdout,
                         "[A] archive/README (4 lines)\n    Review changes.\n")

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
