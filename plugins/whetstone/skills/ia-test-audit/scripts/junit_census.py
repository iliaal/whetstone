#!/usr/bin/env python3
"""Census of a gate run's junit reports: skips by reason, unreported test files, zero-assertion tests.

Reads junit XML written by pytest (--junitxml), PHPUnit (--log-junit), Vitest
(--reporter=junit), jest-junit, or cargo-nextest. Pass --test-files to list test files
on disk that no report mentions: those were never collected by the gate. A file counts
as mentioned only when its path, name, or stem appears between token boundaries, so a
report naming tests/test_user_admin.py does not also mark tests/test_user.py.

Exit status 2 means known incomplete input: an unreadable report, or a --test-files
glob that matched no file. Output is still printed when a glob is unmatched.
"""

from __future__ import annotations

import argparse
import glob
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
    parser.add_argument("--limit", type=int, default=20, help="rows shown per section")
    args = parser.parse_args()

    total = skipped = failed = 0
    skips: dict[str, list[str]] = defaultdict(list)
    zero_assertions: list[str] = []
    mentioned: set[str] = set()
    counts_assertions = False

    for report in args.reports:
        try:
            root = ET.parse(report).getroot()
        except (OSError, ET.ParseError) as error:
            print(f"junit_census: cannot read {report}: {error}; audit input is incomplete", file=sys.stderr)
            return 2
        for suite in root.iter("testsuite"):
            for key in ("name", "file"):
                if suite.get(key):
                    mentioned.add(normalise(suite.get(key, "")))
        for case in root.iter("testcase"):
            total += 1
            parts = [case.get(k, "") for k in ("file", "classname", "name")]
            for part in parts:
                if part:
                    mentioned.add(normalise(part))
                    mentioned.add(normalise(part.replace(".", "/")))
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
        unseen = []
        for name in files:
            path = Path(name)
            stem = normalise(str(path.with_suffix("")))
            candidates = [bounded(c) for c in {stem, normalise(path.name), normalise(path.stem)}]
            if not any(c.search(m) for c in candidates for m in mentioned):
                unseen.append(name)
        print(f"\n== test files on disk never mentioned by any report ({len(unseen)} of {len(files)})")
        print("Check runner include/exclude config, naming conventions, and suite lists.")
        for name in unseen[: args.limit * 5]:
            print(f"  {name}")
    return 2 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
