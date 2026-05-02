#!/usr/bin/env python3
"""Compare external skill/agent repos against the whetstone plugin.

Catalogs components from any Claude Code plugin repo structure, finds overlaps
with our plugin, and generates a structured markdown comparison report.

Usage:
    # Compare all repos in a directory
    python3 scripts/compare-repos.py ../repos/

    # Compare a single repo
    python3 scripts/compare-repos.py ../repos/superpowers

    # Generate report only (skip catalog refresh)
    python3 scripts/compare-repos.py --report-only

    # Show catalog without comparison
    python3 scripts/compare-repos.py --catalog ../repos/agent-skills

    # Filter to skills only or agents only
    python3 scripts/compare-repos.py --type skills ../repos/
    python3 scripts/compare-repos.py --type agents ../repos/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugins" / "whetstone"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".compare-cache"
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Component:
    """A skill or agent found in a repo."""
    kind: str  # "skill" or "agent"
    name: str
    repo: str
    path: str
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    frontmatter: dict = field(default_factory=dict)
    line_count: int = 0
    has_references: bool = False
    reference_files: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# YAML frontmatter parser (no external deps)
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser — handles simple key: value pairs."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            result[key.strip()] = val
    return result


def extract_keywords(text: str, name: str) -> list[str]:
    """Extract likely keywords from skill/agent content."""
    keywords = set()
    # Name parts
    for part in name.replace("-", " ").split():
        if len(part) > 2:
            keywords.add(part.lower())

    # Look for ## headings
    for m in re.finditer(r"^##\s+(.+)$", text, re.MULTILINE):
        heading = m.group(1).strip().lower()
        for word in heading.split():
            word = re.sub(r"[^a-z0-9]", "", word)
            if len(word) > 3:
                keywords.add(word)

    # Look for trigger/keyword sections
    for m in re.finditer(r"(?:trigger|keyword|pattern)[s]?[:\s]+(.+)", text, re.IGNORECASE):
        for word in m.group(1).split(","):
            word = word.strip().strip('"').strip("'").lower()
            if 2 < len(word) < 30:
                keywords.add(word)

    return sorted(keywords)


# ---------------------------------------------------------------------------
# Repo scanners — handle different directory structures
# ---------------------------------------------------------------------------

def scan_skills_dir(skills_dir: Path, repo_name: str) -> list[Component]:
    """Scan a skills/ directory for SKILL.md files."""
    components = []
    if not skills_dir.is_dir():
        return components

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(errors="replace")
        fm = parse_frontmatter(text)
        lines = text.splitlines()

        # Find reference files
        ref_files = []
        for f in skill_dir.rglob("*"):
            if f.is_file() and f.name != "SKILL.md" and f.suffix in (".md", ".txt"):
                ref_files.append(str(f.relative_to(skill_dir)))

        comp = Component(
            kind="skill",
            name=skill_dir.name,
            repo=repo_name,
            path=str(skill_md.relative_to(skill_dir.parent.parent)),
            description=fm.get("description", ""),
            keywords=extract_keywords(text, skill_dir.name),
            frontmatter=fm,
            line_count=len(lines),
            has_references=bool(ref_files),
            reference_files=ref_files,
        )
        components.append(comp)
    return components


def scan_agents_dir(agents_dir: Path, repo_name: str) -> list[Component]:
    """Scan an agents/ directory for agent .md files."""
    components = []
    if not agents_dir.is_dir():
        return components

    for item in sorted(agents_dir.rglob("*.md")):
        if not item.is_file():
            continue
        text = item.read_text(errors="replace")
        fm = parse_frontmatter(text)
        lines = text.splitlines()

        name = item.stem
        comp = Component(
            kind="agent",
            name=name,
            repo=repo_name,
            path=str(item.relative_to(agents_dir.parent)),
            description=fm.get("description", ""),
            keywords=extract_keywords(text, name),
            frontmatter=fm,
            line_count=len(lines),
        )
        components.append(comp)
    return components


def scan_repo(repo_path: Path) -> list[Component]:
    """Auto-detect repo structure and scan for all components."""
    repo_name = repo_path.name
    components = []

    # Structure 1: skills/ and agents/ at root (superpowers, agent-skills, anthropic/skills)
    components.extend(scan_skills_dir(repo_path / "skills", repo_name))
    components.extend(scan_agents_dir(repo_path / "agents", repo_name))

    # Structure 2: plugins/<name>/skills/ and plugins/<name>/agents/ (wshobson, our plugin)
    plugins_dir = repo_path / "plugins"
    if plugins_dir.is_dir():
        for plugin_dir in sorted(plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            plugin_name = f"{repo_name}/{plugin_dir.name}"
            components.extend(scan_skills_dir(plugin_dir / "skills", plugin_name))
            components.extend(scan_agents_dir(plugin_dir / "agents", plugin_name))

    # Structure 3: categories/<name>/<agent>.md (awesome-claude-code-subagents)
    categories_dir = repo_path / "categories"
    if categories_dir.is_dir():
        for cat_dir in sorted(categories_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            components.extend(scan_agents_dir(cat_dir, f"{repo_name}/{cat_dir.name}"))

    return components


# ---------------------------------------------------------------------------
# Similarity matching
# ---------------------------------------------------------------------------

def name_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity between component names."""
    words_a = set(a.replace("-", " ").replace("_", " ").lower().split())
    words_b = set(b.replace("-", " ").replace("_", " ").lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def keyword_similarity(a: list[str], b: list[str]) -> float:
    """Jaccard similarity between keyword sets."""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def combined_similarity(ours: Component, theirs: Component) -> float:
    """Weighted combination of name and keyword similarity."""
    ns = name_similarity(ours.name, theirs.name)
    ks = keyword_similarity(ours.keywords, theirs.keywords)
    # Exact name match gets a bonus
    if ours.name == theirs.name:
        ns = 1.0
    # Weight: name match is more reliable than keyword overlap
    return 0.6 * ns + 0.4 * ks


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------

@dataclass
class Match:
    """A potential overlap between our component and an external one."""
    ours: Component
    theirs: Component
    similarity: float
    size_ratio: float  # theirs.line_count / ours.line_count


def find_overlaps(
    our_components: list[Component],
    external_components: list[Component],
    threshold: float = 0.15,
) -> list[Match]:
    """Find overlapping components above similarity threshold."""
    matches = []
    for ours in our_components:
        for theirs in external_components:
            # Only compare same kind (skill vs skill, agent vs agent)
            if ours.kind != theirs.kind:
                continue
            sim = combined_similarity(ours, theirs)
            if sim >= threshold:
                size_ratio = theirs.line_count / max(ours.line_count, 1)
                matches.append(Match(ours=ours, theirs=theirs, similarity=sim, size_ratio=size_ratio))

    # Sort by similarity descending
    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches


def find_unmatched(
    external_components: list[Component],
    our_components: list[Component],
    threshold: float = 0.15,
) -> list[Component]:
    """Find external components with no match in our plugin."""
    our_names = {c.name for c in our_components}
    unmatched = []
    for ext in external_components:
        best_sim = 0.0
        for ours in our_components:
            if ours.kind != ext.kind:
                continue
            sim = combined_similarity(ours, ext)
            best_sim = max(best_sim, sim)
        if best_sim < threshold and ext.name not in our_names:
            unmatched.append(ext)
    return unmatched


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    our_components: list[Component],
    external_by_repo: dict[str, list[Component]],
    matches: list[Match],
    unmatched: list[Component],
    filter_kind: str | None = None,
) -> str:
    """Generate a markdown comparison report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Repo Comparison Report",
        f"",
        f"Generated: {now}",
        f"",
        f"## Our Plugin Inventory",
        f"",
    ]

    our_filtered = [c for c in our_components if not filter_kind or c.kind == filter_kind]
    for kind in ["skill", "agent"]:
        items = [c for c in our_filtered if c.kind == kind]
        if not items:
            continue
        lines.append(f"### {kind.title()}s ({len(items)})")
        lines.append("")
        lines.append(f"| Name | Lines | References | Keywords (sample) |")
        lines.append(f"|------|------:|:----------:|-------------------|")
        for c in sorted(items, key=lambda x: x.name):
            kw = ", ".join(c.keywords[:5])
            ref = "yes" if c.has_references else "-"
            lines.append(f"| {c.name} | {c.line_count} | {ref} | {kw} |")
        lines.append("")

    # External repos summary
    lines.append("## External Repos Scanned")
    lines.append("")
    for repo_name, components in sorted(external_by_repo.items()):
        filtered = [c for c in components if not filter_kind or c.kind == filter_kind]
        skills = [c for c in filtered if c.kind == "skill"]
        agents = [c for c in filtered if c.kind == "agent"]
        lines.append(f"- **{repo_name}**: {len(skills)} skills, {len(agents)} agents")
    lines.append("")

    # Overlaps
    filtered_matches = [m for m in matches if not filter_kind or m.ours.kind == filter_kind]
    lines.append(f"## Overlapping Components ({len(filtered_matches)} matches)")
    lines.append("")

    if filtered_matches:
        lines.append("| Ours | Theirs | Repo | Sim | Our Lines | Their Lines | Ratio |")
        lines.append("|------|--------|------|----:|----------:|------------:|------:|")
        seen = set()
        for m in filtered_matches:
            key = (m.ours.name, m.theirs.name, m.theirs.repo)
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"| {m.ours.name} | {m.theirs.name} | {m.theirs.repo} "
                f"| {m.similarity:.2f} | {m.ours.line_count} | {m.theirs.line_count} "
                f"| {m.size_ratio:.1f}x |"
            )
        lines.append("")

    # High-similarity matches (likely same skill/agent)
    high_matches = [m for m in filtered_matches if m.similarity >= 0.5]
    if high_matches:
        lines.append("### High-Similarity Matches (>=0.50)")
        lines.append("")
        lines.append("These are likely the same or very similar components. Compare in detail.")
        lines.append("")
        for m in high_matches:
            lines.append(f"- **{m.ours.name}** vs **{m.theirs.name}** ({m.theirs.repo})")
            lines.append(f"  - Similarity: {m.similarity:.2f}")
            lines.append(f"  - Size: {m.ours.line_count} vs {m.theirs.line_count} lines ({m.size_ratio:.1f}x)")
            lines.append(f"  - Our path: `{m.ours.path}`")
            lines.append(f"  - Their path: `{m.theirs.path}`")
            if m.ours.description and m.theirs.description:
                lines.append(f"  - Our desc: {m.ours.description[:100]}")
                lines.append(f"  - Their desc: {m.theirs.description[:100]}")
            lines.append("")

    # Unmatched external components (potential gaps)
    filtered_unmatched = [c for c in unmatched if not filter_kind or c.kind == filter_kind]
    lines.append(f"## Unmatched External Components ({len(filtered_unmatched)} items)")
    lines.append("")
    lines.append("These exist in external repos but have no counterpart in our plugin.")
    lines.append("")

    if filtered_unmatched:
        # Group by repo
        by_repo: dict[str, list[Component]] = {}
        for c in filtered_unmatched:
            by_repo.setdefault(c.repo, []).append(c)

        for repo_name, components in sorted(by_repo.items()):
            lines.append(f"### {repo_name}")
            lines.append("")
            lines.append("| Kind | Name | Lines | Description |")
            lines.append("|------|------|------:|-------------|")
            for c in sorted(components, key=lambda x: (x.kind, x.name)):
                desc = c.description[:80] + "..." if len(c.description) > 80 else c.description
                lines.append(f"| {c.kind} | {c.name} | {c.line_count} | {desc} |")
            lines.append("")

    # Statistics
    lines.append("## Statistics")
    lines.append("")
    total_ext = sum(len(v) for v in external_by_repo.values())
    lines.append(f"- Our components: {len(our_filtered)}")
    lines.append(f"- External components scanned: {total_ext}")
    lines.append(f"- Overlapping matches: {len(filtered_matches)}")
    lines.append(f"- High-similarity (>=0.50): {len(high_matches)}")
    lines.append(f"- Unmatched external: {len(filtered_unmatched)}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cache for incremental runs
# ---------------------------------------------------------------------------

def save_catalog(components: list[Component], cache_path: Path) -> None:
    """Save component catalog to JSON cache."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for c in components:
        data.append({
            "kind": c.kind,
            "name": c.name,
            "repo": c.repo,
            "path": c.path,
            "description": c.description,
            "keywords": c.keywords,
            "line_count": c.line_count,
            "has_references": c.has_references,
            "reference_files": c.reference_files,
        })
    cache_path.write_text(json.dumps(data, indent=2))


def load_catalog(cache_path: Path) -> list[Component]:
    """Load component catalog from JSON cache."""
    if not cache_path.exists():
        return []
    data = json.loads(cache_path.read_text())
    return [
        Component(
            kind=d["kind"],
            name=d["name"],
            repo=d["repo"],
            path=d["path"],
            description=d.get("description", ""),
            keywords=d.get("keywords", []),
            line_count=d.get("line_count", 0),
            has_references=d.get("has_references", False),
            reference_files=d.get("reference_files", []),
        )
        for d in data
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare external repos against whetstone plugin"
    )
    parser.add_argument(
        "repos",
        nargs="*",
        help="Path(s) to external repo(s) or directory containing repos",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Show catalog only, no comparison",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from cached catalogs (skip scanning)",
    )
    parser.add_argument(
        "--type",
        choices=["skills", "agents"],
        help="Filter to skills or agents only",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.15,
        help="Similarity threshold for matches (default: 0.15)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: reports/comparison-YYYY-MM-DD.md)",
    )
    args = parser.parse_args()

    filter_kind = {"skills": "skill", "agents": "agent"}.get(args.type) if args.type else None

    # Scan our plugin
    print("Scanning our plugin...", file=sys.stderr)
    our_components = scan_repo(PLUGIN_ROOT.parent.parent)
    # Filter to only whetstone components
    our_components = [c for c in our_components if "whetstone" in c.repo]
    print(f"  Found {len(our_components)} components", file=sys.stderr)
    save_catalog(our_components, CACHE_DIR / "ours.json")

    if args.report_only:
        # Load from cache
        external_components = load_catalog(CACHE_DIR / "external.json")
        if not external_components:
            print("No cached external catalog. Run without --report-only first.", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.repos:
            print("Provide repo path(s) or use --report-only", file=sys.stderr)
            sys.exit(1)

        # Resolve repo paths
        repo_paths: list[Path] = []
        for r in args.repos:
            p = Path(r).resolve()
            if not p.exists():
                print(f"Path not found: {p}", file=sys.stderr)
                continue
            if not p.is_dir():
                continue
            # Detect if this is a single repo or a directory of repos.
            # Heuristic: if multiple subdirectories have .git/, this is a
            # parent directory containing repos, not a repo itself.
            git_dirs = [
                sub for sub in p.iterdir()
                if sub.is_dir() and (sub / ".git").exists()
            ]
            if len(git_dirs) >= 2:
                is_repo = False
            else:
                has_plugin_marker = (p / ".claude-plugin").exists()
                has_skills = (p / "skills").is_dir() and list((p / "skills").glob("*/SKILL.md"))
                has_plugins = (p / "plugins").is_dir() and list((p / "plugins").rglob("plugin.json"))
                has_categories = (p / "categories").is_dir()
                is_repo = has_plugin_marker or has_skills or has_plugins or has_categories
            if is_repo:
                repo_paths.append(p)
            else:
                # Treat as parent directory containing multiple repos
                for sub in sorted(p.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        repo_paths.append(sub)

        # Scan external repos
        external_components: list[Component] = []
        for repo_path in repo_paths:
            print(f"Scanning {repo_path.name}...", file=sys.stderr)
            components = scan_repo(repo_path)
            print(f"  Found {len(components)} components", file=sys.stderr)
            external_components.extend(components)

        save_catalog(external_components, CACHE_DIR / "external.json")

    if args.catalog:
        # Just print the catalog
        for c in sorted(external_components, key=lambda x: (x.repo, x.kind, x.name)):
            kind_marker = "S" if c.kind == "skill" else "A"
            print(f"[{kind_marker}] {c.repo}/{c.name} ({c.line_count} lines)")
            if c.description:
                print(f"    {c.description[:100]}")
        return

    # Group external by repo
    external_by_repo: dict[str, list[Component]] = {}
    for c in external_components:
        repo_key = c.repo.split("/")[0] if "/" in c.repo else c.repo
        external_by_repo.setdefault(repo_key, []).append(c)

    # Find overlaps
    print("Finding overlaps...", file=sys.stderr)
    matches = find_overlaps(our_components, external_components, threshold=args.threshold)
    print(f"  Found {len(matches)} matches", file=sys.stderr)

    # Find unmatched
    unmatched = find_unmatched(external_components, our_components, threshold=args.threshold)
    print(f"  Found {len(unmatched)} unmatched external components", file=sys.stderr)

    # Generate report
    report = generate_report(our_components, external_by_repo, matches, unmatched, filter_kind)

    # Output
    if args.output:
        out_path = Path(args.output)
    else:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = REPORT_DIR / f"comparison-{date_str}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"\nReport written to {out_path}", file=sys.stderr)

    # Also print summary to stdout
    our_skills = len([c for c in our_components if c.kind == "skill"])
    our_agents = len([c for c in our_components if c.kind == "agent"])
    ext_skills = len([c for c in external_components if c.kind == "skill"])
    ext_agents = len([c for c in external_components if c.kind == "agent"])
    high = len([m for m in matches if m.similarity >= 0.5])
    print(f"\nSummary:")
    print(f"  Ours: {our_skills} skills, {our_agents} agents")
    print(f"  External: {ext_skills} skills, {ext_agents} agents")
    print(f"  Overlaps: {len(matches)} total, {high} high-similarity")
    print(f"  Gaps: {len(unmatched)} unmatched external components")


if __name__ == "__main__":
    main()
