---
name: announce
description: Draft X/Twitter announcement post (or thread) for the latest plugin release
argument-hint: "[optional: version to announce, defaults to current]"
---

# Draft release announcement for X

Generate an announcement post for the latest compound-engineering plugin release. The account is X Premium — one long post usually covers a release; only thread when a second distinct theme justifies the visual pacing. Apply the `writing` skill throughout — no filler, no AI slop, no throat-clearing.

## Step 1: Gather context

1. Read the current version from `plugins/compound-engineering/.claude-plugin/plugin.json`
2. Read CHANGELOG.md -- extract entries for the version being announced (default: current version). If multiple versions were released in the same session, combine them into one announcement.
3. Get the ai-skills repo version: `cd ~/ai/ai-skills && git log --oneline -1 && cd -`
4. Count components: `bash scripts/update-metadata.sh`

## Step 2: Draft the post

The account is X Premium — each post can hold up to 25,000 characters, so most releases fit in one post. Thread only when a second distinct theme genuinely benefits from visual pacing, not to chunk content that belongs together.

**Single post structure (preferred):**

Open with the bookend (version + component counts + install links) — this is what shows in the feed before "Show more." Front-load the hook in the first ~250 chars; everything below that is only seen by readers who click through.

- compound-engineering + ai-skills vX.Y.Z (if versions match, list once; if different, list both)
- Component counts: N agents, N commands, N skills
- Install: `claude plugins add iliaal/compound-engineering-plugin`
- Portable skills: `npx skills add https://github.com/iliaal/ai-skills`
- Link to github.com/iliaal/compound-engineering-plugin

After the bookend, list the user-visible changes grouped by theme:

- Focus on what changed that users will notice. Skip internals.
- Group by theme, not by file. Within each theme, 2-5 bullets max.
- Lead each bullet with the user benefit, not the implementation detail
- Skip internal changes (script fixes, comment updates, metadata, trigger tests, regex expansions) unless they affect users
- Small release (1-3 changes)? A compact single post is fine. Don't pad to fill the character budget.
- Practical ceiling: ~5,000 chars per post reads well. Beyond that, readers disengage even on Premium. Hard technical ceiling is 25,000.

**Thread fallback (only when justified):**

Split across multiple posts when the release has two or more clearly distinct themes that benefit from visual pacing in the feed — not because one post would be "too long." Each continuation post still gets the Premium character budget; don't chunk at 280.

- No tweet should exceed 25,000 characters (hard Premium limit)
- No artificial chunking — if content belongs together, keep it together

## Step 3: Apply writing skill

Invoke the `writing` skill and run every tweet through it. The skill catches em dashes, AI filler, passive voice, and throat-clearing that are easy to miss in short-form copy. Do not skip this step or substitute a manual check.

## Step 4: Present for review

Show the complete post (or thread) with character counts per post. Flag any post over 24,500 chars (leave headroom under the 25,000 Premium limit). Separately flag any post where the first 250 chars don't stand alone as a coherent hook — that's what the feed shows before "Show more."

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

1. Write the approved tweets to `/tmp/thread-vX.Y.Z.json` (JSON array of strings).
2. Launch Edge with the dedicated compound-engineering profile + CDP debug port, if not already running:
   ```bash
   bash scripts/launch-edge.sh
   ```
   Profile lives at `C:\Users\ilia\edge-compound-engineering` on the Windows side (local disk, not the WSL 9P bridge) on CDP port 9225. First run: log in to X in the opened window; subsequent runs reuse the session.
3. Compose the thread (types all tweets, does NOT click Post):
   ```bash
   python3 scripts/post-thread.py /tmp/thread-vX.Y.Z.json
   ```
   The script detects login state. If not logged in, it opens the login page and exits -- log in, then re-run.
4. Tell the user the draft is ready and to review + click Post in the Edge window.

**Important:** Close all Edge windows before the first launch. Edge ignores `--remote-debugging-port` if an instance is already running.
