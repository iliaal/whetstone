#!/usr/bin/env python3
"""Generate SPEC.md per skill from SKILL.md + trigger fixtures (Tier 2 Commit B).

Output structure (7 required headings, mirrors skill-writer):
  ## Intent
  ## Scope
  ## Trigger Context
  ## Source And Evidence Model
  ## Evaluation
  ## Known Limitations
  ## Maintenance Notes
"""
import json
import re
from pathlib import Path

SKILLS_DIR = Path("plugins/whetstone/skills")
FIXTURES_DIR = Path("distillery/tests/fixtures/triggers")

CLASS_BLURBS = {
    "language": "stack-specific patterns and idioms",
    "discipline": "an engineering practice not tied to one stack",
    "workflow": "a multi-step process producing concrete artifacts",
    "meta": "patterns about prompts, agents, or skills themselves",
    "tool": "a narrow utility scoped to a single capability",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].splitlines():
        m = re.match(r"^([a-z-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith(">-"):
            continue
        fm[key] = val.strip(" '\"")
    body = parts[2].strip()
    if "description" not in fm:
        m = re.search(r"^description:\s*>-?\s*\n((?:  .*\n?)+)", parts[1], re.MULTILINE)
        if m:
            fm["description"] = " ".join(ln.strip() for ln in m.group(1).splitlines() if ln.strip())
    return fm, body


def load_fixture_samples(skill: str) -> tuple[list[str], list[str]]:
    path = FIXTURES_DIR / f"{skill}.jsonl"
    if not path.exists():
        return [], []
    pos: list[str] = []
    neg: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        (pos if e.get("expect") else neg).append(e.get("prompt", ""))
    return pos[:3], neg[:3]


def detect_refs(skill_dir: Path) -> int:
    refs = skill_dir / "references"
    if not refs.is_dir():
        return 0
    return sum(1 for p in refs.rglob("*.md"))


def render_spec(skill: str, fm: dict, body: str, klass: str, ref_count: int,
                pos_samples: list[str], neg_samples: list[str]) -> str:
    desc = fm.get("description", "").strip()
    blurb = CLASS_BLURBS.get(klass, "patterns")

    def quote_list(items: list[str]) -> str:
        if not items:
            return "<!-- to fill in: representative phrasings -->"
        return "\n".join(f"  - \"{q}\"" for q in items)

    coverage_rows = [
        ("Trigger fixtures", "complete",
         f"distillery/tests/fixtures/triggers/{skill}.jsonl (>=5 should_trigger, >=5 should_not_trigger)"),
        ("Hook regex pattern", "complete",
         f"plugins/whetstone/hooks/skill-patterns.sh (`SKILL_PATTERNS[{skill}]`)"),
        ("Reference architecture",
         "complete" if ref_count > 0 else "n/a",
         f"{ref_count} file(s) under references/" if ref_count else "no references; SKILL.md is self-contained"),
        ("Real-usage signal",
         "<!-- populated by harvest-sessions when sessions exist -->",
         f"distillery/.eval-data/{skill}/ (created by harvest-sessions)"),
    ]
    coverage_table = "\n".join(f"| {dim} | {status} | {ev} |" for dim, status, ev in coverage_rows)

    return f"""# {skill} Specification

## Intent

`{skill}` is a `{klass}`-class skill ({blurb}). {desc}

## Scope

In scope:
- Behaviors described in `SKILL.md` and routed via the should_trigger phrasings in `distillery/tests/fixtures/triggers/{skill}.jsonl`.
- Updates to runtime behavior, structure, trigger precision, references, and validation.

Out of scope:
- Acting as the runtime instructions themselves (those live in `SKILL.md`).
- Trigger phrasings already covered by adjacent `ia-*` skills (`validate-plugin` flags >70% description overlap as DUPLICATE_TRIGGER).
- <!-- to fill in: domain-specific exclusions when the skill drifts -->

## Trigger Context

- Class: `{klass}`
- Hook regex: `plugins/whetstone/hooks/skill-patterns.sh` -> `SKILL_PATTERNS[{skill}]`
- Common requests (from fixture should_trigger):
{quote_list(pos_samples)}
- Should not trigger for (from fixture should_not_trigger):
{quote_list(neg_samples)}

## Source And Evidence Model

Authoritative sources:

- `SKILL.md` -- runtime instructions and reference routing.
- `references/*.md` -- bundled supplementary content ({ref_count} file(s)).
- `distillery/tests/fixtures/triggers/{skill}.jsonl` -- positive and negative trigger phrasings under regression test.
- `plugins/whetstone/hooks/skill-patterns.sh` -- regex pattern that fires this skill.
- `distillery/.eval-data/{skill}/` -- harvested session examples (when present).

Data that must not be stored in this skill or its references:

- Secrets, credentials, tokens.
- Machine-specific filesystem paths (`/home/...`, `/Users/...`, `~/ai/...`). The validator (`MACHINE_PATH_LEAK`) flags these as HIGH.
- Private URLs, customer data, or unredacted personal information.

### Coverage matrix

| Dimension | Status | Evidence |
|---|---|---|
{coverage_table}

## Evaluation

Lightweight (run on every change):

```bash
python3 distillery/scripts/distiller.py validate-plugin --component {skill}
python3 distillery/scripts/distiller.py test-triggers --skill {skill}
```

Deeper (when behavior risk warrants):

```bash
python3 distillery/scripts/distiller.py dspy-eval {skill}
python3 distillery/scripts/distiller.py diagnose-negatives {skill}
```

Acceptance gates:
- `validate-plugin --component {skill}` returns 0 HIGH findings.
- `test-triggers --skill {skill}` returns F1 = 1.0 with floors of 5 should_trigger and 5 should_not_trigger.
- For dspy-eval, the composite score does not regress against the most recent saved baseline (see `distillery/.eval-data/{skill}/history.json`).

## Known Limitations

<!-- to fill in over time as drift surfaces. Default rule: any time diagnose-negatives
     surfaces a recurring failure pattern, document it here so future maintainers
     understand the trade-off the current implementation accepts. -->

## Maintenance Notes

- Update `SKILL.md` when the runtime workflow, branch conditions, or output contract changes.
- Update this `SPEC.md` when intent, scope, evidence model, evaluation gates, or maintenance expectations change.
- Update the trigger fixture when adding new positive phrasings, removing stale ones, or expanding scope (the 5/5 floor is a hard validator gate).
- Update the hook regex in `skill-patterns.sh` whenever fixture positives expose a missed phrasing; verify F1 = 1.0 with `eval-triggers` before committing.
- Run the full release pipeline via `/release` -- never bump versions or update CHANGELOG.md from a per-skill edit.
"""


def main() -> None:
    written = 0
    skipped = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        spec_md = skill_dir / "SPEC.md"
        if spec_md.exists():
            print(f"  skip (already exists): {skill_dir.name}")
            skipped += 1
            continue

        text = skill_md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        klass = fm.get("class", "generic")
        if not fm.get("description"):
            full = re.search(r"description:\s*(?:>-?\s*)?\n((?:  [^\n]+\n?)+)", text)
            if full:
                fm["description"] = " ".join(ln.strip() for ln in full.group(1).splitlines() if ln.strip())

        pos, neg = load_fixture_samples(skill_dir.name)
        ref_count = detect_refs(skill_dir)
        spec = render_spec(skill_dir.name, fm, body, klass, ref_count, pos, neg)
        spec_md.write_text(spec, encoding="utf-8")
        print(f"  + SPEC.md  {klass:11s}  {skill_dir.name}  ({len(spec.splitlines())} lines)")
        written += 1

    print(f"\nWrote {written} SPEC.md, skipped {skipped} (already existed).")


if __name__ == "__main__":
    main()
