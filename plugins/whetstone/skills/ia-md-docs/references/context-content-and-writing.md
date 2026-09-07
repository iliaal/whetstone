# Context content and writing

## What Belongs in Context Files

Keep AGENTS.md / CLAUDE.md to durable signal. Do NOT enumerate:

- **Installed skills, plugins, or extensions** -- these change with the user's environment, not the project; the list rots within weeks.
- **Tool versions outside the project's source of truth** -- `package.json` engines, `.nvmrc`, `pyproject.toml` Python constraint, `composer.json` PHP version. List the source-of-truth file path; do not duplicate the version inline.
- **Linter / formatter rule restatements** -- if `.eslintrc`, `ruff.toml`, `phpcs.xml` already enforce it, the file is the spec. List the command to run; do not paraphrase rules.
- **README content** -- if information is already in README.md (install, badges, intro), reference it; do not re-paste.

The test: if a fact will be wrong in two months without anyone touching this file, it does not belong here.

What earns the space is the inverse: document what the agent cannot discover by reading the repo -- the unwritten convention, the reason behind a choice, the gotcha no config file confesses. The environment is a source of truth too, so a section restating it is a cache, and a cache earns its load only when the lookup is expensive. Naming the one test command among forty `package.json` scripts is an expensive lookup and belongs here (see Commands below); a raw `ls -R` dump or a paraphrase of `--help` is a cheap one the agent can re-derive on demand. A curated structure note -- what a new top-level directory is *for* -- is not the same thing, and still belongs here.

Treat fewer words as an optimization signal, not an acceptance criterion. Before condensing or merging rules in a context file, capture a baseline and predeclare the decisions the file exists to control: request authority, external actions, when to ask, proof standards, failure attribution. Compare baseline and candidate on the same cases; any safety, authority, or honesty regression rejects the candidate however much smaller it is. Prefer merging duplicated rules and deleting procedural restatement; preserve exact wording where it is what changes behavior. Change one rule group at a time, and add a case when a new failure mode appears rather than growing the file pre-emptively.

A fact any flow might need belongs in the always-loaded context file, not in the one sub-document whose flow needs it today; a cross-cutting convention recorded only as a comment at one call site is invisible at the next. Put the shared fact in the file every session loads, and enforce a cross-site rule at the shared initialization point rather than restating it per site.


## Context File Hierarchy

Structure CLAUDE.md (and AGENTS.md) content by priority so the most critical information loads first when context is compacted:

1. **Rules** -- project constraints, forbidden patterns, required conventions. Override everything else.
2. **Tech stack** -- languages, frameworks, package managers (versions: see above).
3. **Commands** -- how to build, test, lint, deploy. Exact commands, not descriptions.
4. **Conventions** -- naming patterns, file organization, architectural decisions.
5. **Boundaries** -- what's off-limits, what requires approval, scope constraints.

Rules that prevent mistakes outweigh background information.


## Writing Style

- **Lead with the answer.** First sentence of each section states the conclusion; reasoning follows. No "In this section, we'll..." preamble.
- **Imperative form** for instructions: "Build the project" not "The project is built" — verify no passive voice in any directive sentence.
- **One directive per sentence.** A rule that bundles two actions gets half-applied: the reader acts on the first clause and the last, and drops the middle. Move any sequence of 3+ steps into a numbered list rather than burying it in prose.
- **`must`/`never` for requirements, `should`/`may` for latitude.** A requirement phrased as "should" reads as optional and gets skipped.
- **Expert-to-expert**: cut explanations of concepts the target reader already knows. For CLAUDE.md/AGENTS.md, assume familiarity with git, package managers, test runners, and the project's main language.
- **Scannable**: headings every ~20 lines, bullet lists for ≥3 parallel items, fenced code blocks for every command.
- **Verify every command and path against the codebase.** Run each command before committing; grep for each referenced path. Stale paths and untested commands are the most common doc defect.
- **Verify every external identifier, not just internal paths.** A cited upstream PR, issue, RFC, or release tag is a claim about someone else's repository: open it and confirm the title matches what the sentence says it is. Shorthand that merely *looks* canonical (`PR-120`, `issue 99`) is the usual failure — it gets treated as the real ID by everything downstream and fans out into every artifact built from that file. Write the canonical form (`owner/repo#N`), and re-verify state claims ("merged", "fixed in") before publishing, since those rot fastest. One lookup per cited ID is cheaper than correcting the same wrong link in N places after it ships.
- **Sentence case headings**, no emoji decoration in CLAUDE.md/AGENTS.md/CONTRIBUTING/DOCS; README headers may carry at most one conventional emoji per header (see ia-writing's README rules); changelog entries may use emoji per project convention.
- **Actionable headings**: "Set SAML before adding users" — not "SAML configuration timing". Reader should know what to do from the heading alone.
- **Collapse depth** with `<details>` blocks instead of deleting content (blank line required after `<summary>` for GitHub rendering).
- **Treat every published snippet as a test.** Code in a README or docs page is never exercised by the suite, so it drifts to a missing method or a wrong output. Extract every snippet and every stated output into one script and run it against the built artifact before publishing; keep runnable copies next to the code. Audit the reverse direction separately -- features that shipped and were never documented.


## README Anti-Patterns

Flag during `Update README` workflows:
- Framework-first lead (explaining the tech stack before the problem it solves)
- Jargon before definition (using project-specific terms without introduction)
- Theory before try (architecture explanation before a working example)
- Claims without evidence ("blazingly fast" with no benchmarks)
- Changelog-speak, in both directions -- forward-looking hype ("now supports", "new in 3.2", "coming soon") and backward-looking narration of a diff ("this replaced the previous approach", "X was refactored to use Y"). A README describes the tool's present tense; a reader without the commit history gets archaeology instead of a description. Version-migration notes belong in CHANGELOG or `docs/`, and CHANGELOG, release notes, migration guides, and decision records are exempt -- being version-scoped is their purpose
