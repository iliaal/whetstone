---
name: announce
description: Draft X/Twitter announcement thread for the latest plugin release
argument-hint: "[optional: version to announce, defaults to current]"
---

# Draft release announcement for X

Generate a thread of tweets announcing the latest compound-engineering plugin release. Apply the `writing` skill throughout -- no filler, no AI slop, no throat-clearing.

## Step 1: Gather context

1. Read the current version from `plugins/compound-engineering/.claude-plugin/plugin.json`
2. Read CHANGELOG.md -- extract entries for the version being announced (default: current version). If multiple versions were released in the same session, combine them into one announcement.
3. Get the ai-skills repo version: `cd ~/ai/ai-skills && git log --oneline -1 && cd -`
4. Count components: `bash scripts/update-metadata.sh`

## Step 2: Draft the thread

**Tweet 1 (bookend -- version + install + links):**
- compound-engineering + ai-skills vX.Y.Z (if versions match, list once; if different, list both)
- Component counts: N agents, N commands, N skills
- Install: `claude plugins add iliaal/compound-engineering-plugin`
- Portable skills: `npx skills add https://github.com/iliaal/ai-skills`
- Link to github.com/iliaal/compound-engineering-plugin
- No process details (no "synced from N repos", no "N files changed"). Just the version, what's in the box, and how to get it.

**Tweets 2+N (key changes only):**
- Focus on what changed that users will notice. Skip internals.
- Group by theme, not by file
- Each tweet: one theme, 2-3 bullet points max
- Lead each bullet with the user benefit, not the implementation detail
- Skip internal changes (script fixes, comment updates, metadata, trigger tests, regex expansions) unless they affect users
- No tweet should exceed 280 characters
- If the release is small (1-3 changes), a single follow-up tweet is fine. Don't pad.

## Step 3: Apply writing skill

Invoke the `writing` skill and run every tweet through it. The skill catches em dashes, AI filler, passive voice, and throat-clearing that are easy to miss in short-form copy. Do not skip this step or substitute a manual check.

## Step 4: Present for review

Show the complete thread with character counts per tweet. Flag any tweet over 270 chars (leave room for formatting).

Format:
```
Tweet 1 (XXX chars):
[text]

Tweet 2 (XXX chars):
[text]

...
```

Do not post anything. Present for user approval only.

## Step 5: Post to X

After user approves the thread:

1. Write the approved tweets to a JSON file: `/tmp/thread-vX.Y.Z.json` (array of strings)
2. Launch Edge with debug port (if not already running):
   ```bash
   "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
       --remote-debugging-port=9225 --remote-debugging-address=0.0.0.0 \
       --remote-allow-origins=* --user-data-dir=/tmp/edge-profile &
   ```
3. If first time, open login page and wait for user to log in:
   ```bash
   python3 scripts/post-thread.py /tmp/thread-vX.Y.Z.json
   ```
   The script detects login state. If not logged in, it opens the login page and exits.
4. Compose the thread (types all tweets, does NOT post):
   ```bash
   python3 scripts/post-thread.py /tmp/thread-vX.Y.Z.json
   ```
5. Ask user to review the composed thread in the browser
6. When user confirms, post:
   ```bash
   python3 scripts/post-thread.py /tmp/thread-vX.Y.Z.json --post-now
   ```

Edge session persists at `/tmp/edge-profile`. Subsequent runs in the same session skip login.

**Important:** Close all Edge windows before the first launch. Edge ignores `--remote-debugging-port` if an instance is already running.
