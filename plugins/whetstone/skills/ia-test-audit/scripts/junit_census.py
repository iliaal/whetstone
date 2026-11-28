#!/usr/bin/env python3
"""Census of a gate run's junit reports: skips by reason, unreported test files, zero-assertion tests.

Reads junit XML written by pytest (--junitxml), PHPUnit (--log-junit), Vitest
(--reporter=junit), jest-junit, or cargo-nextest. Pass --test-files to list test files
on disk that no report mentions. Prefer a reported path or qualified module, then use
bounded names or stems when unique. Colliding short names are reported separately.

Exit status 2 means known incomplete input: an unreadable report, or a --test-files
glob that matched no file. Output is still printed when a glob is unmatched.
"""

from __future__ import annotations

import argparse
import glob
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {
    "node_modules",
    "vendor",
    ".git",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".claude",
    ".next",
    ".turbo",
    ".worktrees",
}


def expand(patterns: list[str]) -> list[str]:
    """Glob, dropping dependency, build, and agent-worktree directories."""
    found = {f for p in patterns for f in glob.glob(p, recursive=True)}
    return sorted(f for f in found if Path(f).is_file() and not SKIP_DIRS.intersection(Path(f).parts))


def normalise(text: str) -> str:
    return text.replace("\\", "/").replace("::", "/").lower()


def bounded(candidate: str) -> re.Pattern[str]:
    """Match a path, name, or stem only where it is not part of a longer token."""
    return re.compile(rf"(?<![\w-]){re.escape(candidate)}(?![\w-])")


def path_key(text: str) -> str:
    return posixpath.normpath(os.path.normcase(text).replace("\\", "/").replace("::", "/"))


def qualified_matches(labels: tuple[str, ...], aliases: dict[str, set[str]]) -> set[str]:
    matches: set[str] = set()
    for label in labels:
        while "/" in label:
            if label in aliases:
                matches.update(aliases[label])
                break
            label = label.rsplit("/", 1)[0]
    return matches


def collection_evidence(
    files: list[str], mentions: set[tuple[str, tuple[str, ...]]]
) -> tuple[set[str], set[str]]:
    paths: dict[str, set[str]] = defaultdict(set)
    modules: dict[str, set[str]] = defaultdict(set)
    basenames: dict[str, set[str]] = defaultdict(set)
    stems: dict[str, set[str]] = defaultdict(set)
    working_dir = Path.cwd()
    for name in files:
        path = Path(name)
        absolute = Path(os.path.abspath(path))
        spellings = {absolute}
        if absolute.is_relative_to(working_dir):
            spellings.add(absolute.relative_to(working_dir))
        for spelling in spellings:
            key = path_key(spelling.as_posix())
            if "/" in key:
                paths[key].add(name)
                modules[normalise(str(spelling.with_suffix("")))].add(name)
        basenames[normalise(path.name)].add(name)
        stems[normalise(path.stem)].add(name)

    short_patterns = [
        [(bounded(key), matches) for key, matches in aliases.items()]
        for aliases in (basenames, stems)
    ]
    confirmed: set[str] = set()
    ambiguous: set[str] = set()
    for file, labels in mentions:
        explicit = path_key(file) if file else ""
        if "/" in explicit:
            matches = paths.get(explicit, set())
        else:
            short_labels = tuple(map(normalise, (*labels, file)))
            matches = (
                qualified_matches(tuple(map(path_key, labels)), paths)
                or qualified_matches(tuple(label.replace(".", "/") for label in short_labels), modules)
                or basenames.get(normalise(explicit), set())
            )
            if not matches:
                for patterns in short_patterns:
                    matches = {
                        name for pattern, candidates in patterns
                        if any(pattern.search(label) for label in short_labels)
                        for name in candidates
                    }
                    if matches:
                        break
        if len(matches) == 1:
            confirmed.update(matches)
        else:
            ambiguous.update(matches)
    return confirmed, ambiguous - confirmed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("reports", nargs="+", help="junit XML files from the gate run")
    parser.add_argument(
        "--test-files",
        action="append",
        default=[],
        metavar="GLOB",
        help="glob (repeatable, ** allowed) of test files expected to be collected",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="detail row limit (non-negative; 0 hides details; unseen files use 5x)",
    )
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be non-negative")

    total = skipped = failed = 0
    skips: dict[str, list[str]] = defaultdict(list)
    zero_assertions: list[str] = []
    mentioned: set[tuple[str, tuple[str, ...]]] = set()
    counts_assertions = False

    for report in args.reports:
        try:
            root = ET.parse(report).getroot()
        except (OSError, ET.ParseError) as error:
            print(f"junit_census: cannot read {report}: {error}; audit input is incomplete", file=sys.stderr)
            return 2
        for suite in root.iter("testsuite"):
            mentioned.add((suite.get("file", ""), (suite.get("name", ""),)))
        for case in root.iter("testcase"):
            total += 1
            mentioned.add((case.get("file", ""), (case.get("classname", ""), case.get("name", ""))))
            ident = "::".join(p for p in (case.get("classname"), case.get("name")) if p)
            skip = case.find("skipped")
            if skip is not None:
                skipped += 1
                reason = (skip.get("message") or skip.text or "(no reason)").strip()
                reason = re.sub(r"\s+", " ", reason)[:200]
                skips[reason].append(ident)
            elif case.find("failure") is not None or case.find("error") is not None:
                failed += 1
            if case.get("assertions") is not None:
                counts_assertions = True
            if case.get("assertions") == "0" and skip is None:
                zero_assertions.append(ident)

    print(f"testcases {total}  skipped {skipped}  failed/errored {failed}")

    print(f"\n== skip reasons ({len(skips)} distinct)")
    print("A reason that is constant in the gate environment (build profile, unset env var,")
    print("tool the gate never installs) makes every test under it dead in the gate.")
    for reason, cases in sorted(skips.items(), key=lambda kv: -len(kv[1]))[: args.limit]:
        print(f"{len(cases):5d}  {reason}")
        for ident in cases[:3]:
            print(f"         e.g. {ident}")

    if counts_assertions:
        print(f"\n== executed tests reporting zero assertions ({len(zero_assertions)})")
        for ident in zero_assertions[: args.limit]:
            print(f"  {ident}")

    unmatched: list[str] = []
    if args.test_files:
        pattern_files = [(pattern, expand([pattern])) for pattern in args.test_files]
        files = sorted({name for _, names in pattern_files for name in names})
        unmatched = [pattern for pattern, names in pattern_files if not names]
        for pattern in unmatched:
            print(f"junit_census: unmatched pattern (no eligible files): {pattern}", file=sys.stderr)
        confirmed, ambiguous = collection_evidence(files, mentioned)
        unseen = sorted(set(files) - confirmed - ambiguous)
        print(f"\n== test files on disk never mentioned by any report ({len(unseen)} of {len(files)})")
        print("Check runner include/exclude config, naming conventions, and suite lists.")
        for name in unseen[: args.limit * 5]:
            print(f"  {name}")
        if ambiguous:
            print(f"\n== test files with collection ambiguous from short names ({len(ambiguous)})")
            print("Use a reporter with file paths or verify these files in the runner's collection listing.")
            for name in sorted(ambiguous)[: args.limit * 5]:
                print(f"  {name}")
    return 2 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
