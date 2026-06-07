#!/usr/bin/env python3
"""Advisory report: which skills compete for the same trigger vocabulary.

Borrowed from Waza's `check_trigger_overlap` (pairwise Jaccard on trigger
keywords), adapted to whetstone's reality: triggers live as regex in
`plugins/whetstone/hooks/skill-patterns.sh`, not as keyword bags, and the
`ia-` language family legitimately shares stack vocabulary. So this is an
advisory report, not a hard gate.

It complements the existing tooling:
  - test-triggers (JSONL fixtures) answers "does phrase X fire skill Y?"
  - analyze-misfires answers "was skill Y injected where it wasn't needed?"
    (post-hoc, on harvested sessions)
  - this answers "do skills Y and Z compete for the same phrases?"
    (static, at authoring time, before any session data exists)

Tokens are the literal alphabetic runs inside each skill's regex (alternation
arms, word sequences), minus regex noise and stopwords. Jaccard = shared /
union over those token sets. Pairs are ranked descending; pairs where both
skills sit in the same SKILL_TIERS bucket are flagged [same-tier] because
stack-family overlap there is expected, not a defect.

Usage:
  python3 scripts/check-trigger-overlap.py [--threshold 0.10] [--top 25]
                                           [--patterns <path>] [--strict]

Exit code is 0 (advisory) unless --strict is passed, which exits 1 when any
cross-tier pair meets the threshold (a genuine collision between unrelated
skills).
"""

from __future__ import annotations

import argparse
import re
import sys
from itertools import combinations
from pathlib import Path

PATTERN_RE = re.compile(r"^SKILL_PATTERNS\[([a-z0-9-]+)\]='(.*)'\s*$")
TIER_RE = re.compile(r"^SKILL_TIERS\[([a-z0-9-]+)\]=(\d+)\s*$")
TOKEN_RE = re.compile(r"[a-z]{3,}")

# Regex-structural words and routing-generic stopwords that carry no
# skill-distinguishing signal. Kept conservative on purpose.
STOPWORDS = frozenset({
    "the", "this", "that", "with", "for", "and", "you", "your", "are", "has",
    "have", "let", "lets", "need", "want", "make", "made", "into", "out",
    "via", "use", "used", "using", "any", "all", "new", "from", "not", "but",
    "should", "would", "could", "when", "what", "why", "how", "who",
})


def extract_tokens(pattern: str) -> set[str]:
    """Literal alphabetic tokens in a trigger regex, minus noise and stopwords.

    Regex metacharacters contribute no [a-z]{3,} runs (\\b, \\s, .{0,30},
    (?:...) all lack 3+ letter sequences), so a simple letter-run scan over
    the lowercased pattern recovers the literal trigger words.
    """
    return {t for t in TOKEN_RE.findall(pattern.lower()) if t not in STOPWORDS}


def parse_patterns(path: Path) -> tuple[dict[str, set[str]], dict[str, int]]:
    tokens: dict[str, set[str]] = {}
    tiers: dict[str, int] = {}
    for line in path.read_text().splitlines():
        m = PATTERN_RE.match(line)
        if m:
            tokens[m.group(1)] = extract_tokens(m.group(2))
            continue
        m = TIER_RE.match(line)
        if m:
            tiers[m.group(1)] = int(m.group(2))
    return tokens, tiers


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=float, default=0.10,
                        help="Minimum Jaccard to report (default: 0.10). whetstone's "
                             "triggers are well-separated; 0.10 surfaces genuine "
                             "near-neighbors, higher values quickly go empty.")
    parser.add_argument("--top", type=int, default=25,
                        help="Max pairs to print (default: 25)")
    parser.add_argument("--patterns", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "plugins" / "whetstone" / "hooks" / "skill-patterns.sh")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any cross-tier pair meets the threshold")
    args = parser.parse_args()

    if not args.patterns.is_file():
        print(f"ERROR: patterns file not found: {args.patterns}", file=sys.stderr)
        return 2

    tokens, tiers = parse_patterns(args.patterns)
    if not tokens:
        print(f"ERROR: no SKILL_PATTERNS parsed from {args.patterns}", file=sys.stderr)
        return 2

    pairs = []
    for a, b in combinations(sorted(tokens), 2):
        score = jaccard(tokens[a], tokens[b])
        if score >= args.threshold:
            same_tier = tiers.get(a) is not None and tiers.get(a) == tiers.get(b)
            shared = sorted(tokens[a] & tokens[b])
            pairs.append((score, a, b, same_tier, shared))

    pairs.sort(reverse=True, key=lambda p: p[0])

    print(f"Trigger-overlap report ({len(tokens)} skills, threshold={args.threshold})")
    print("  [same-tier] = both skills share a stack family; overlap there is expected.")
    print("  Unflagged pairs are cross-tier collisions worth a closer look.\n")

    if not pairs:
        print(f"No skill pairs at or above Jaccard {args.threshold}.")
        return 0

    cross_tier_hits = 0
    for score, a, b, same_tier, shared in pairs[:args.top]:
        tag = " [same-tier]" if same_tier else " [CROSS-TIER]"
        if not same_tier:
            cross_tier_hits += 1
        shown = ", ".join(shared[:8]) + ("..." if len(shared) > 8 else "")
        print(f"  {score:.2f}{tag}  {a} <-> {b}")
        print(f"        shared: {shown}")

    if len(pairs) > args.top:
        print(f"\n  ... {len(pairs) - args.top} more pair(s) below the top {args.top}.")

    print(f"\n{cross_tier_hits} cross-tier pair(s) at/above threshold "
          f"out of {len(pairs)} total.")

    if args.strict and cross_tier_hits:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
