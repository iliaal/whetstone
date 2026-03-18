---
name: skill-distiller
description: >-
  Fetches top-rated skills from skills.sh, analyzes them, and synthesizes one
  token-efficient skill combining the best elements. Use when the user asks to
  "distill skills for X", "find and combine skills for X", "synthesize skills",
  "merge skills", "make a skill for X from skills.sh", "update distilled skill",
  or mentions combining, distilling, or synthesizing multiple skills into one
  token-efficient skill.
---

# Skill Distiller

Fetches top-rated skills from skills.sh for a task, analyzes them, and synthesizes one token-efficient skill combining the best elements.

## Modes

### Distill `<query>`

**1. Search** — Find qualifying skills:

```bash
python3 distillery/scripts/distiller.py search "<query1>" "<query2>" ...
```

Returns JSON array of qualifying skills (filtered to `installs >= 100`, top 10, deduplicated). If fewer than 3 qualify, threshold drops to 50. Save this output — it feeds into Step 2.

**1b. Triage before fetching** — High install count does not correlate with quality. Before fetching, scan the search results: read skill descriptions and source repo names. Skip sources that are clearly generic checklists, project-specific tools, or domains outside the target skill's scope. Only fetch sources that suggest genuinely new patterns or techniques.

**2. Fetch** — Stage sources and compute checksums:

```bash
python3 distillery/scripts/distiller.py fetch --skills '<JSON from Step 1>'
```

Handles grouping by source, running `npx skills add`, staging to `distillery/.skill-distiller/sources/`, removing symlinks, and computing SHA-1 checksums. Returns JSON array with `id`, `skillId`, `installs`, `sha1`, and `path` for each staged source.

**Fetch fallback:** If `distillery/scripts/distiller.py fetch` fails (subprocess issues with `npx skills add`), run `npx skills add <source_url> -s <skillId> -y --agent claude-code` directly from the project root. The skill will be installed to `.claude/skills/<skillId>/`. Read the SKILL.md from there, then clean up the directory after analysis.

**2b. Grok query** — Query recent X posts for practitioner insights:

```bash
python3 distillery/scripts/distiller.py grok-query "<topic>" --top-installs <N>
```

Pass `--top-installs` using the highest install count from Step 1 results (sets engagement threshold: >=10k→50 likes, >=1k→10 likes, <1k→3 likes). Optionally pass `--instructions` if user provided scope/exclusion rules. Returns JSON with `findings` (categorized as `breaking_change`, `emerging_pattern`, `pitfall`, `new_tooling`) and a `summary`. Use findings as supplementary context during analysis — not a formal source, but a "did we miss anything?" signal. If no findings, skip with no impact.

**3. Analyze** — Read each staged `SKILL.md`. Extract per skill:
- Core techniques (actionable patterns unique to this skill)
- Unique value (what others lack)
- Failed approaches / anti-patterns with reasons — these are high-value; failure paths save more time than success paths
- Filler ratio (verbose examples, generic advice, redundancy)
- "Claude already knows this" — flag content that explains things Claude inherently knows (what a PDF is, how HTTP works, what a database does). This is the highest-signal filler detector.

**3b. Resolve conflicts** — When sources contradict each other (e.g., opposing patterns, mutually exclusive approaches), do NOT silently pick one. For each conflict, prompt the user with:
- The conflicting positions and which source skills hold them
- A recommendation with brief rationale
- Let the user decide before proceeding to synthesis

**Clarification discipline** — Do not over-clarify. Ask only when critically needed:
- **Ask if**: sources fundamentally contradict on architecture (e.g., class-based vs functional), the user's scope is ambiguous enough to produce a wrong skill, or a decision irreversibly shapes the output
- **Don't ask if**: you can infer from context, the choice is low-impact and easily revised, you have a clear best default, or asking would just be seeking permission to proceed

**4. Synthesize** — Generate `SKILL.md` with YAML frontmatter. Use this exemplar as the structural reference:

````markdown
---
name: simplifying-code
description: >-
  Simplifies, polishes, and declutters code without changing behavior. Use when
  asked to "simplify code", "clean up code", "polish code", "refactor",
  "declutter", "reduce complexity", "remove dead code", "remove AI slop",
  "improve readability", or "tighten up this file".
---

# Simplifying Code

## Principles

| Principle | Rule |
|-----------|------|
| **Preserve behavior** | Output must do exactly what the input did — no silent feature additions or removals |
| **Surgical changes** | Touch only what needs simplifying. Match existing style |

## Process

1. **Read first** — understand the full file and its dependents before changing anything
2. **Identify invariants** — what must stay the same? Public API, return types, side effects
3. **Apply in order** — structural changes first, cosmetic last
4. **Verify** — confirm no behavior change: tests pass, types check

## Smell → Fix

| Smell | Fix |
|-------|-----|
| Deep nesting (>2 levels) | Guard clauses with early returns |
| Long function (>30 lines) | Extract into named functions by responsibility |
| Dead code / unreachable branches | Delete entirely — no commented-out code |

## Constraints

- Only simplify what was requested — do not add features or expand scope
- If a simplification would make the code harder to understand, skip it
````

Notice: keyword-saturated description with synonyms, imperative voice throughout, tables for dense pattern→action mappings, measurable criteria (">2 levels", ">30 lines"), no filler. Match this density and structure.

Frontmatter: only `name` and `description`. Strip all inert metadata (triggers, role, scope, domain, output-format, author, version, license, related-skills) — Claude Code ignores these and they waste tokens. No "pairs well with" or "related skills" lines — the user knows what complements their workflow.

Name constraints:
- Prefer gerund form (verb+-ing): `processing-pdfs`, `building-react-apps`, `managing-databases`. Acceptable alternatives: noun phrases (`pdf-processing`) or action-oriented (`process-pdfs`)
- Max 64 characters, lowercase letters + numbers + hyphens only
- Must not contain "anthropic" or "claude"

Description constraints:
- < 80 tokens
- Third person ("Processes Excel files and generates reports")
- Structure: `[what the skill does]. [when to use it with trigger phrases in quotes].` Both halves are required — capabilities help Claude understand what the skill provides, triggers help it match user intent
- **Keyword saturation** — the description is the entire selection mechanism (no embeddings, no classifiers). Systematically include synonyms and alternate phrasings a user might say. "Excel" alone misses "spreadsheet", "xlsx", "tabular data", "pivot table".

Body constraints (< 1K tokens ideal, 2K hard cap):
- **Critical instructions first** — place the most important rules at the top of the body; middle content gets lost in long contexts due to attention curves
- **Minimize directive count** — adherence drops to ~50% at 10+ discrete rules. Consolidate aggressively: fewer rules with more context beats many terse rules. Count directives in the output and merge where possible.
- Imperative rules > explanatory prose
- Checklists > paragraphs
- Code examples only when pattern is non-obvious
- No "when to use" sections (description handles activation)
- No filler, no redundancy — every line must earn its tokens
- Merge overlapping techniques across sources; preserve unique ones
- Never use second person ("you should...")

Formulation principles (apply to every generated skill):
- **Surface assumptions** — if a source technique has implicit prerequisites or trade-offs, make them explicit in the output rather than silently adopting them
- **Minimum necessary** — include only what the task demands; no speculative features, unnecessary abstractions for single-use patterns, unrequested configurability, or error handling for impossible cases
- **Surgical merging** — when combining sources, preserve each skill's existing style and intent; don't refactor working patterns into a different paradigm just for uniformity
- **Goal-driven rules** — translate vague advice ("write clean code") into measurable criteria ("functions < 40 lines, single responsibility, named for what they return")
- **Degrees of freedom** — match specificity to fragility. Fragile operations (exact CLI commands, migrations) get exact instructions with no room for interpretation. Heuristic tasks (code review, analysis) get high-level direction and trust Claude's judgment.
- **Defaults over options** — when sources offer competing tools/approaches for the same thing, pick the best default. Mention one escape hatch for the main alternative, not a menu of 5 choices.
- **Consistent terminology** — pick one term per concept across merged sources. If one says "endpoint" and another says "route", choose one and use it everywhere.
- **No naked negations** — every "don't do X" must include "do Y instead." Without the alternative, Claude gets stuck. Prohibitions without a path forward are dead weight.

**4b. Validate & self-review** — After writing the initial SKILL.md, two passes:

**Pass 1 — Mechanical** (run `python3 distillery/scripts/distiller.py validate <name>`):
Returns a 7-gate score (frontmatter, name, description, token_budget, no_placeholders, completeness, manifest). Pass threshold: 6/7. Fix any failed gates before continuing. Warnings are advisory — review but don't necessarily fix.

**Pass 2 — Re-read and check against synthesis rules.** For each check, fix inline if found:
- **"Claude already knows this"** — remove lines explaining what the technology is, how basic concepts work, or general programming knowledge. A React skill shouldn't explain what components are.
- **Vague directives** — rewrite any unmeasurable advice ("write clean code", "keep it simple", "follow best practices") into specific criteria, or remove.
- **Naked negations** — every "don't X" must have "do Y instead". Add the alternative or remove the line.
- **Filler / redundancy** — cut lines that repeat what another line already says in different words. Cut generic advice that applies to all programming, not specifically this topic.
- **Description keyword gaps** — does the description cover the synonyms and alternate phrasings a user would actually say? Add missing trigger phrases.
- **Directive count** — count discrete rules/instructions. If > 10, consolidate — merge related rules into fewer, richer statements.
- **Second person** — replace "you should..." with imperative form.
- **Time-sensitive content** — flag version-pinned statements ("as of v3.2", "since 2024", "if using React 18"), date-dependent advice, and deprecated-vs-current bifurcations. Either remove the version qualifier to state the pattern as current default, or move to a collapsible "legacy patterns" section if historical context is needed.

After fixes, re-run `validate` to confirm issues are resolved.

**Pass 3 — Split check.** Check token count (`python3 distillery/scripts/distiller.py token-count <file>`):

- **Body <= 1K tokens**: no split needed, proceed to Save.
- **Body > 1K and <= 2K tokens**: propose a split into `references/`. Present to user:
  - Which sections move to which reference files (named `references/<topic>.md`, kebab-case)
  - What stays in SKILL.md (frontmatter + highest-priority ~500-700 tokens — critical instructions that must be seen first due to attention curves)
  - Estimated tokens per file
  - Wait for user approval before splitting. If user declines, keep as single file.
- **Body > 2K tokens**: split is required. Same proposal format, but frame as mandatory. If user adjusts the proposed grouping, apply their version. After splitting, iteratively trim lowest-value content from any file still over 2K.

Split rules:
- Each reference file covers one cohesive topic section (e.g., `testing.md`, `state-management.md`, `security.md`)
- Max one level deep — no nested references
- Link reference files from SKILL.md body as markdown links (e.g., `See [security](references/security.md) for details`). Do NOT add a `references:` field to frontmatter — only `name` and `description` belong there; anything else is inert metadata
- Each reference file: < 2K tokens, no frontmatter needed, starts with `# Section Title`
- SKILL.md body should still be self-contained enough to be useful without references — references add depth, not completeness

**5. Save** — Write outputs:

- Write `distillery/generated-skills/<query>/SKILL.md` — the synthesized skill
- Write `distillery/generated-skills/<query>/manifest.json` with initial content:
  ```json
  {
    "query": "<query>",
    "search_queries": ["<query1>", "<query2>", ...],
    "generated": "<ISO 8601 date>",
    "token_count": <estimated>,
    "instructions": "<user-provided scope, exclusions, and focus directives — omit if none>",
    "sources": [
      { "id": "owner/repo/skill-name", "installs": 6329, "sha1": "<sha1 from Step 2>" }
    ]
  }
  ```
  `search_queries` — all search keywords used during the Search phase (enables re-search on update). `instructions` — user-provided exclusion rules, scope narrowing, and focus directives that shaped source selection and synthesis (applied during both generation and updates). `sha1` — SHA-1 of the fetched source `SKILL.md` (enables change detection on update). Use `sha1` and `installs` values from Step 2 fetch output.

**6. Evaluate** — A/B comparison against baseline. Generate 3 test prompts that minimize token usage while revealing whether the model internalized the skill's rules:
- **Outline prompt**: ask for a plan/approach, not full code (e.g., "Outline the structure for a FastAPI service with background jobs — list files, key decisions, and which patterns you'd use")
- **Decision prompt**: force a choice that tests the skill's defaults and opinions (e.g., "I need state management in React — what approach and why?")
- **Review prompt**: provide a short snippet that violates 2-3 skill rules and ask the model to identify issues (e.g., "Review this: `async def get_users(): data = await db.fetch_all(); return data` — what would you change?")

Avoid prompts that ask for full implementations — they burn tokens testing code generation, not skill adherence. The goal is to check: does the model follow the skill's terminology, defaults, anti-patterns, and decision frameworks?

Present the prompts to the user. If they approve testing, run:

```bash
python3 distillery/scripts/distiller.py ab-eval <name> --prompts '<JSON array of 3 prompts>'
```

Sends each prompt to 4 models via OpenRouter, twice per model: once with the skill as system prompt (treatment), once without (baseline). Override models with `--models '["model/id", ...]'`. Requires `OPENROUTER_API_KEY` in `.env`.

Compare paired results: for each prompt x model, how does the treatment differ from baseline?
- Did the skill's terminology and patterns appear in treatment but not baseline?
- Did the skill's defaults and opinions shape decisions in treatment?
- Did the review prompt catch the planted violations in treatment?
- Were there any regressions where baseline was actually better?

If all models produce similar treatment vs baseline improvements, the skill has clear signal. If some models ignore key instructions, the skill may need more explicit guidance on those points.

**6b. Trigger evaluation** (optional, run after saving to plugin) — Generate trigger evaluation queries: realistic user prompts that should and shouldn't activate this skill. Test against the regex pattern in `skill-patterns.sh`:

```bash
python3 distillery/scripts/distiller.py eval-triggers <name> --queries '{"should_trigger": [...], "should_not_trigger": [...]}'
```

Review precision/recall/F1 metrics. If false negatives are high, the pattern needs more trigger terms. If false positives are high, the pattern is too broad. Iterate on the pattern in `skill-patterns.sh` until F1 >= 0.8.

**6c. Improvement loop** (if 6 revealed weaknesses) — If A/B results show the skill failed to influence model behavior on specific points:
1. Identify which rules were ignored or which patterns weren't followed
2. Analyze why: was the instruction buried in the middle? too vague? contradicted by another rule?
3. Make targeted edits to SKILL.md — move critical rules higher, make vague instructions specific, resolve contradictions
4. Re-run `python3 distillery/scripts/distiller.py validate <name>` to confirm mechanical correctness
5. Re-run `ab-eval` with the same prompts to verify improvement
6. Max 3 iterations — if improvement plateaus, accept the current version

**7. Cleanup** — `python3 distillery/scripts/distiller.py cleanup`

**8. Present** — Show the generated skill with description token count, body token count, and the path: `distillery/generated-skills/<query>/SKILL.md`

### Update `<name>`

1. **Check for updates** — Single command handles manifest reading, re-search, re-fetch, and checksum comparison:

```bash
python3 distillery/scripts/distiller.py check-updates <name>
```

Returns JSON with `status` (`"no_updates"` or `"updates_available"`), plus categorized sources: `unchanged`, `changed` (with `path`), `new` (with `path`), `removed`, and `instructions` if set. If `"no_updates"` → continue to Grok query (step 1b) to check for recent practitioner insights even if sources haven't changed. If both have nothing → stop.

1b. **Grok query** — Run `python3 distillery/scripts/distiller.py grok-query "<topic>" --top-installs <N>` (same as Distill step 2b). Use findings as supplementary context during analysis.

2. **Analyze & present changes** — Read only the changed/new source files (use `path` from check-updates output). Apply `instructions` from the output when filtering content. Include relevant Grok findings. For each meaningful change, present:
   - What changed in the source (or what the new source adds)
   - **Pro**: what incorporating this improves
   - **Con**: token cost increase, potential redundancy, reduced focus
   - Recommendation: incorporate / skip / replace existing section
   Flag conflicts between new/changed content and existing skill content — show both positions with sources and recommend a resolution before applying.
3. **Apply** — If user approves → regenerate skill, then run full step 4b (mechanical validate, self-review, split check). Then update the manifest:

```bash
python3 distillery/scripts/distiller.py update-manifest <name> --token-count <N> --sources '<JSON array with id, installs, sha1>'
```

4. **Cleanup** — `python3 distillery/scripts/distiller.py cleanup`
