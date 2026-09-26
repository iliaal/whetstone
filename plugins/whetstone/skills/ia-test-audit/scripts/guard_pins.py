#!/usr/bin/env python3
"""List refusal messages in source that no test asserts.

A guard whose message appears in no test is either untested or tested only by a
status-only negative, which a different guard's refusal would also satisfy. The count
sizes the problem. Individual rows are candidates: the extraction also picks up warnings
and format fragments (over-count), and a short generic test needle can look like a pin
(under-count).

Source literals are taken from lines that look like a refusal (throw, raise, abort,
Err(, bail!, exit, reject, deny, ValidationException, ...) and the two lines after
them, so multi-line calls are covered. Test needles are every string literal in the
test files. In Rust files, everything after the first `#[cfg(test)]` counts as test
code, not source.

Exit status 2 means known incomplete input: a --src or --tests glob matched no file.
Output is still printed.
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from collections import Counter
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


GUARD_LINE = re.compile(
    r"\b(?:throw|raise|abort(?:_if|_unless)?|bail!|panic!|Err\(|Failure|fail|reject|deny|refuse|exit|die|"
    r"withMessages|withErrors|ValidationException|HttpException|AuthorizationException|Error\(|report_and_exit)",
    re.IGNORECASE,
)
DOUBLE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
SINGLE = re.compile(r"'((?:[^'\\\n]|\\.)*)'")
BACKTICK = re.compile(r"`((?:[^`\\]|\\.)*)`")
HOLE = re.compile(r"\{[^{}]*\}|%[sdifx]|\$\{[^}]*\}|\$\w+|\{\d*\}")


def literals(line: str, suffix: str) -> list[str]:
    found = [m.group(1) for m in DOUBLE.finditer(line)]
    if suffix not in (".rs",):
        found += [m.group(1) for m in SINGLE.finditer(line)]
    if suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        found += [m.group(1) for m in BACKTICK.finditer(line)]
    return found


def split_rust(text: str) -> tuple[str, str]:
    m = re.search(r"^\s*#\[cfg\(test\)\]", text, re.MULTILINE)
    return (text, "") if m is None else (text[: m.start()], text[m.start() :])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src", action="append", required=True, metavar="GLOB", help="production source glob"
    )
    parser.add_argument("--tests", action="append", default=[], metavar="GLOB", help="test file glob")
    parser.add_argument("--min-length", type=int, default=20, help="shortest source literal considered")
    parser.add_argument("--needle-min", type=int, default=12, help="shortest test literal counted as a pin")
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="REGEX", help="skip literals matching"
    )
    parser.add_argument("--limit", type=int, default=60, help="unpinned rows printed")
    args = parser.parse_args()

    pattern_files = [(pattern, expand([pattern])) for pattern in [*args.src, *args.tests]]
    unmatched = [pattern for pattern, names in pattern_files if not names]
    for pattern in unmatched:
        print(f"guard_pins: unmatched pattern (no eligible files): {pattern}", file=sys.stderr)
    src_files = expand(args.src)
    test_files = expand(args.tests)
    excludes = [re.compile(x) for x in args.exclude]

    needles: set[str] = set()
    guards: list[tuple[str, int, str]] = []

    for name in test_files:
        suffix = Path(name).suffix
        for line in Path(name).read_text(errors="replace").splitlines():
            needles.update(n for n in literals(line, suffix) if len(n) >= args.needle_min)

    for name in src_files:
        suffix = Path(name).suffix
        text = Path(name).read_text(errors="replace")
        if suffix == ".rs":
            text, test_part = split_rust(text)
            for line in test_part.splitlines():
                needles.update(n for n in literals(line, suffix) if len(n) >= args.needle_min)
        lines = text.splitlines()
        window = 0
        for number, line in enumerate(lines, 1):
            if GUARD_LINE.search(line):
                window = 3
            if window:
                window -= 1
                for literal in literals(line, suffix):
                    if len(literal) >= args.min_length and not any(x.search(literal) for x in excludes):
                        guards.append((name, number, literal))

    seen: set[str] = set()
    unpinned: list[tuple[str, int, str]] = []
    for name, number, literal in guards:
        if literal in seen:
            continue
        seen.add(literal)
        fragments = [f.strip() for f in HOLE.split(literal) if len(f.strip()) >= args.needle_min]
        pinned = any(n in literal or any(n in f for f in fragments) for n in needles)
        if not pinned:
            unpinned.append((name, number, literal))

    per_file = Counter(name for name, _, _ in unpinned)
    print(
        f"{len(seen)} distinct guard literals in {len(src_files)} source files; "
        f"{len(unpinned)} contain no test string literal (>= {args.needle_min} chars)"
    )
    print(f"{len(needles)} test needles from {len(test_files)} test files\n")
    print("== unpinned by file")
    for name, count in per_file.most_common(25):
        print(f"{count:5d}  {name}")
    print(f"\n== first {args.limit} unpinned")
    for name, number, literal in unpinned[: args.limit]:
        print(f"{name}:{number}  {literal[:120]}")
    return 2 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
