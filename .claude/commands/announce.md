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

**Tweet 1 (hook + repos):**
- Lead with what users can now DO, not what changed internally
- **Always include both repo URLs in Tweet 1** (non-negotiable):
  - github.com/iliaal/compound-engineering-plugin (with version)
  - github.com/iliaal/ai-skills (portable skills mirror)
- Include component counts (N agents, N commands, N skills)
- End with a hook for the thread

**Tweets 2+N (key changes):**
- Group changes by theme, not by file
- Each tweet: one theme, 2-3 bullet points max
- Lead each bullet with the user benefit, not the implementation detail
- Skip internal changes (script fixes, comment updates, metadata) unless they affect users
- No tweet should exceed 280 characters

**Final tweet:**
- How to install: `claude plugins add iliaal/compound-engineering-plugin`
- Or for portable skills only: `npx skills add https://github.com/iliaal/ai-skills`

## Step 3: Apply writing skill

Review the draft against the `writing` skill principles:
- Kill AI patterns: no "excited to announce", "we're thrilled", "game-changing"
- No emoji-decorated headers
- Lead with what the user can do, not what was built
- Active voice, name actors
- Cut filler: if a word adds nothing, delete it

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
