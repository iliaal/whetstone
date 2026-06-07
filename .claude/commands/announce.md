---
name: announce
description: Draft X/Twitter announcement post (or thread) for the latest plugin release
argument-hint: "[optional: version to announce, defaults to current]"
---

# Draft release announcement for X

Generate an announcement post for the latest whetstone plugin release. The account is X Premium — one long post usually covers a release; only thread when a second distinct theme justifies the visual pacing.

This command is the dedicated X drafter for whetstone releases. For other repos, other platforms, or non-release posts (benchmark drops, opinion takes, real-time engagement), use `/ia-promote <repo> <platform>` instead.

## Step 0: Load promotion-workspace rules

Before drafting, read these to anchor voice, platform constraints, and ethics:

- `~/ai/promotion/rules/platforms/x.md` — X-specific rules (Premium char limits, hook discipline, when to thread vs single-post)
- `~/ai/promotion/rules/voice.md` — voice rules (directness, density, banned constructions)
- `~/ai/promotion/rules/ethics.md` — non-negotiables (no shadow personas, no manufactured urgency, no fake testimonials, no manufactured social proof)
- `~/ai/promotion/rules/humanizer-check.md` — anti-AI-detection patterns specific to social posts

When this command's inline guidance disagrees with those rules, the rules win — the rules are the canonical source, this command is the orchestration wrapper. Apply the `ia-writing` skill throughout for prose hygiene (no filler, no AI slop, no throat-clearing).

Also check `~/ai/promotion/announcement-matrix.md` for the whetstone row. If `Last announced` already equals the version being drafted, ask the user whether to skip, redraft anyway, or target a different version.

## Step 1: Gather context

1. Read the current version from `plugins/whetstone/.claude-plugin/plugin.json`
2. Read CHANGELOG.md -- extract entries for the version being announced (default: current version). If multiple versions were released in the same session, combine them into one announcement.
3. Get the ai-skills repo version: `cd ~/ai/ai-skills && git log --oneline -1 && cd -`
4. Count components: `bash scripts/update-metadata.sh`

## Step 2: Draft the post

X posts are marketing. Assume the reader is scrolling a busy feed — you have the first ~250 characters to earn a click-through. Craft them as a compelling hook that tells the reader what this release is about and why they should care. Everything past that is only read by readers who already opted in.

The account is X Premium (25,000 character limit per post), so most releases fit in one post. Thread only when a second distinct theme genuinely benefits from visual pacing, not to chunk content that belongs together.

**Target 1,500-2,500 chars for most releases.** Rich releases (10+ user-visible changes) condense into 3-5 top-impact bullets plus a link to the full CHANGELOG — do not list every change. Small releases (1-3 user-visible changes) fit in ~800-1,200 chars and skip the changelog link. Practical ceiling is 3,500 chars; beyond that you trade reader attention for completeness.

**Single post structure:**

1. **Opener (first ~250 chars, the feed preview — marketing copy that has to earn the click):**
   - Version line: `whetstone vX.Y.Z` (add `+ ai-skills` only if versions differ)
   - **Thematic hook**: one sentence enumerating the themes this release touches (e.g., "Sharper rules for deploys, code review, swarm orchestration, frontend discipline, and scope creep"). **Never cut the hook when trimming.** It's the attention bait for feed scrollers and maps top-level themes so a reader can self-select what matters.
   - Component counts: N agents, N commands, N skills
   - Top-N pivot line (e.g., "Top 5:") introducing the bullets

2. **Body (the 3-5 top-impact bullets):**
   - Focus on what changed that users will notice. Skip internals.
   - Group by theme, not by file. One bullet per theme, 1-3 sentences max.
   - Lead each bullet with the user benefit, not the implementation detail.
   - Skip internal changes (script fixes, comment updates, metadata, trigger tests, regex expansions) unless they affect users.

3. **Full-changelog link with theme teaser** (rich releases only):
   - One line pointing at the CHANGELOG with a parenthetical teaser of 3-5 themes NOT covered in the top-N bullets.
   - Format: `Full changelog (theme-A, theme-B, theme-C, and the rest): github.com/iliaal/whetstone/blob/master/CHANGELOG.md`
   - The teaser lets readers judge whether clicking through will find what they need.

4. **Install commands:**
   - `Install: /plugin marketplace add https://github.com/iliaal/whetstone && /plugin install whetstone@iliaal-marketplace && /reload-plugins`
   - `Portable skills: npx skills add iliaal/ai-skills`

5. **Repo URL footer (standalone final line):**
   - `github.com/iliaal/whetstone`
   - On its own line, separated from install commands by a blank line. Acts as a click target for readers who want the repo after scanning the post.

**Thread fallback (only when justified):**

Split across multiple posts when the release has two or more clearly distinct themes that benefit from visual pacing in the feed — not because one post would be "too long." Each continuation post still gets the Premium character budget; don't chunk at 280.

- No tweet should exceed 25,000 characters (hard Premium limit)
- No artificial chunking — if content belongs together, keep it together

## Step 3: Apply writing skill

Invoke the `ia-writing` skill in audit mode on the drafted post. The skill returns an AUDIT (tagged offenses), CORRECTED TEXT, and 5-dimension scores (Directness / Rhythm / Trust / Authenticity / Density, 1-10 each). Present the audit alongside the corrected draft so the reader can see what was fixed and why.

Expect the score to land above 40/50 before presenting. If below, run another pass focusing on the weakest dimension.

**Note on changelog-style false agency.** Changelog bullets routinely use concept-as-subject ("Action Routing replaces the Fix-First binary", "feature flags now require…") which the writing skill flags as FALSE-AGENCY. For announcement bullets, accept concept-as-subject when the concept IS the shipped artifact (a skill, a pattern, a rule). Rewrite to actor-first (`you`, `we`, imperative) only when doing so adds clarity — don't force it when the original is already direct.

Always fix: em dashes, AI lexicon (delve, crucial, pivotal, leverage, seamless, robust, etc.), passive voice when an actor exists, and adverb filler (silently, explicitly, absolutely, etc.).

## Step 4: Present for review

Show the complete post (or thread) with character counts per post. Three checks, all required:

1. **Length**: flag any post over 3,500 chars (practical reader-engagement ceiling — warn that condensing with a changelog link will read better). Flag any post over 24,500 chars (hard Premium-limit headroom).
2. **Feed-preview hook**: flag any post whose first 250 chars don't stand alone as a compelling marketing hook — that's what the feed shows before "Show more," and it must earn the click-through on its own.
3. **Writing-skill score**: state the 5-dimension score from Step 3. If below 40/50, re-run before presenting.

Format:
```
Post 1 (XXX chars):
[text]

(if thread)
Post 2 (XXX chars):
[text]

...
```

Do not post anything. Present for user approval only.

## Step 5: Draft in X

After user approves the thread, draft it into X for manual review and posting. Claude never clicks Post -- the user does that in the browser.

1. Write the approved tweets to `~/ai/whetstone/.announce/thread-vX.Y.Z.json` (JSON array of strings). `.announce/` is gitignored and persists across reboots, unlike `/tmp` which wipes on system restart.
2. Ensure the `compound-engineering` Edge profile is running (no-op if already up):
   ```bash
   bash scripts/launch-edge.sh
   ```
   Thin wrapper for `edge-cdp ensure compound-engineering`. The profile is bound to `@iliaa` on CDP port 9225 and was intentionally not renamed during the v4.0.0 plugin rename — browser sessions, login cookies, and per-platform composer state all live in that profile dir. First run: log in to X in the opened window; subsequent runs reuse the session. Profile registry and CDP framework details: `~/ai/wiki/tools/edge-automation.md`.
3. Compose the thread (types all tweets, does NOT click Post):
   ```bash
   python3 scripts/post-thread.py ~/ai/whetstone/.announce/thread-vX.Y.Z.json
   ```
   The script auto-launches the profile if needed and detects login state. If not logged in, it opens the login page and exits -- log in, then re-run.
4. Tell the user the draft is ready and to review + click Post in the Edge window.

Different profiles on different CDP ports run in parallel. The `pinescript` profile on 9229 can stay open while `compound-engineering` runs on 9225.

## Step 6: Stamp the announcement matrix

After the user manually clicks Post in X and confirms it landed, the post needs to be recorded so future `/ia-announce-scan` runs don't re-flag this version as needing a draft. Tell the user:

> "Post it in the Edge window when you're ready. Once it's live, run `/ia-announced whetstone x` to stamp the matrix."

Do not stamp the matrix yourself — `/ia-announced` is the canonical command and it cross-checks `gh release list` for the version. Stamping before the post actually goes up creates a false-positive in the matrix that future scans rely on.
