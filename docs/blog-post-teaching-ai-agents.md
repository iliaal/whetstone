# Teaching AI Agents How to Engineer

Every AI coding agent ships with the same problem: it knows syntax but not discipline. It can write a React component or debug a segfault, but it won't ask "did I verify this actually works?" before declaring victory. It won't split a 400-line diff into reviewable chunks. It won't check if the fix it's about to apply matches the root cause it claims to have found.

I've spent the past six months fixing that.

[compound-engineering](https://github.com/iliaal/compound-engineering-plugin) is a Claude Code plugin, and [ai-skills](https://github.com/iliaal/ai-skills) is its portable counterpart for 35+ AI coding agents. Together they encode the engineering judgment that separates "code that compiles" from "code you'd ship."

## What's in the box

The compound-engineering plugin ships 29 skills, 20 specialized agents, and 22 commands. Skills are compact instruction sets that fire based on what you're working on. Agents are purpose-built reviewers and researchers. Commands wire them into repeatable workflows.

The ai-skills repo extracts just the skills into a format any agent can consume: Claude Code (what I use), Codex, OpenCode, and anything else with skills support. One install command, zero configuration.

```bash
# Portable skills for any agent
npx skills add iliaal/ai-skills

# Full plugin for Claude Code
claude plugins add iliaal/compound-engineering-plugin
```

## Skills aren't prompts

A skill looks like a markdown file. It acts like a behavioral contract.

Take the [debugging](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/debugging) skill. Its core rule: no fix until you've identified the root cause with file-and-line evidence, two levels deep in the call chain. The agent must reproduce the bug first, test one hypothesis at a time, and escalate to the user after three failed attempts instead of guessing forever.

The [code-review](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/code-review) skill runs a two-stage process: spec compliance first, then code quality. When a diff crosses three complexity thresholds (300+ lines, 8+ files, touches security or migrations), it dispatches parallel specialist agents. A security reviewer, a performance analyst, a database guardian, and a maintainability auditor all examine the same diff independently, then merge their findings with deduplication.

The [writing](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/writing) skill maintains a kill-on-sight vocabulary list. "Delve," "leverage," "robust," "seamless," words that signal machine output. It catches structural tells too: forced triads, dramatic fragments, synonym cycling. Every piece of prose passes through a five-dimension scoring rubric before delivery.

These aren't suggestions. They're process gates. The agent can't skip them.

Good prompts still matter, though. Skills encode discipline, but the quality of what you ask for shapes the output just as much. I don't always get that right, so I built a [refine-prompt](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/refine-prompt) skill that transforms vague instructions into precise, structured ones. It's the skill I use on my own prompts before committing them as commands or workflow steps.

## How skills activate

Token budget matters. You don't always have a 1M context window, and even when you do, filling it with instructions leaves less room for the actual work. So I put real effort into compression.

At startup, only skill descriptions load into context. Each description is tuned to the minimum token count that still lets the agent match it to the right request. Too short and the skill never fires. Too long and you're burning context on 29 descriptions before the conversation starts. Finding that line took weeks of testing and iteration.

When your request matches a skill's keywords, the full body pulls in. Ask about a React component and the [react-frontend](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/react-frontend) skill fires. Start debugging and the debugging skill loads with its reproduction-first protocol.

The skills themselves follow the same principle. Core rules live in the SKILL.md body, kept under a 1K token target with a 2K hard cap. Detailed reference material, decision trees, pattern libraries, and extended examples go into `references/` files that only load when the agent needs them. The code-review skill's security patterns, the debugging skill's competing-hypotheses framework, the writing skill's full banned-phrase list: all stored as references, pulled only when the agent needs them.

The plugin takes this further with a hook that intercepts agent dispatches. When the code-review command spawns a security-sentinel agent, the hook injects the relevant skills into that agent's context before it starts work. No manual invocation needed. Fresh agents inherit methodology on dispatch.

A three-tier priority system prevents overload: methodology skills (code-review, debugging) outrank domain skills (react-frontend, [python-services](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/python-services)), which outrank supporting skills ([writing-tests](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/writing-tests), [verification](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/verification-before-completion)). Cap of five per injection. The agent gets exactly the discipline it needs without drowning in instructions.

## The workflow loop

Five commands form the development cycle:

`/workflows:brainstorm` interviews you one question at a time, produces two or three named approaches with trade-offs, and outputs a design document.

`/workflows:plan` turns that into atomic tasks with specific file paths, phased into vertical slices capped at five to eight files each.

`/workflows:work` executes the plan with task tracking, worktree isolation for parallel work, and verification gates after every task.

`/workflows:review` runs the multi-agent code review described above.

`/workflows:compound` captures the solution as searchable documentation in `docs/solutions/`, so the next time someone hits the same problem, a research agent finds it.

Each command works standalone. You don't need the full loop for a quick review or a focused debugging session.

There's a sixth command that sits outside the development cycle but drives the whole project forward: [reflect](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/reflect). I run it after every big session. It walks through the full conversation, flags mistakes and friction points, identifies where skills fell short or triggered when they shouldn't have, and proposes fixes. Those findings feed directly into the next release: skill rewrites, hook regex tweaks to reduce false triggers, new memory entries so the agent doesn't repeat the same mistake twice. Most of the 75 releases trace back to something `/reflect` surfaced from a real session.

## Built from real use, not theory

This isn't a weekend project that got a README. It's 342 commits across 75 releases since October 2025. Roughly one release every 2.4 days for six months.

Every release responds to something that happened in practice. The code-review skill is diagnostic-only because auto-fixing introduced regressions. The debugging skill caps attempts at three because without that limit, agents would silently try 15 broken fixes before asking for help. The writing skill's banned-phrase list grows every time I catch the agent producing "in today's rapidly evolving landscape."

The plugin includes a skill distillery that automates this refinement loop. It harvests session logs from actual Claude Code usage, scores skill effectiveness via LLM-as-judge evaluation, and can evolve skills through DSPy optimization. A regression suite with 179 trigger-pattern tests gates every release. If a skill fires when it shouldn't, or doesn't fire when it should, the release fails.

## What it covers

The skills span the stacks I work in and the problems I hit most:

**Languages and frameworks**: [React 19](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/react-frontend) with App Router patterns, [Node.js backend](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/nodejs-backend) architecture (Express, Fastify, Hono), [Python services](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/python-services) with FastAPI, [PHP/Laravel](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/php-laravel), [Tailwind CSS](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/tailwind-css), even [Pine Script](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/pinescript) for TradingView.

**Engineering process**: [planning](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/planning) with vertical slicing, code review with specialist dispatch, debugging with root-cause discipline, test writing, verification gates.

**Infrastructure**: [PostgreSQL](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/postgresql) performance and schema design, [Terraform](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/terraform), [Linux/bash scripting](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/linux-bash-scripting), Docker, cloud architecture across AWS/Azure/GCP.

**AI-native patterns**: [multi-agent orchestration](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/orchestrating-swarms), [agent-native architecture](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/agent-native-architecture) audits, [meta-prompting](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/meta-prompting) techniques, skill refinement workflows.

Each skill encodes opinions. The [PHP skill](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/php-laravel) mandates `declare(strict_types=1)` everywhere and PHPStan level 8+. The [Node.js skill](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/nodejs-backend) enforces layered architecture with no cross-layer HTTP imports. The [React skill](https://github.com/iliaal/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/react-frontend) routes "should I use an effect?" questions through a decision tree that almost always answers "no." These aren't generic best practices scraped from documentation. They're the rules that prevent the bugs I've watched agents introduce.

## Why portable skills matter

AI coding agents are proliferating. Most developers will use two or three over the next year, depending on context. Skills that only work in one tool create vendor lock-in for your engineering standards.

The ai-skills repo solves this. Install once, and your debugging discipline, review process, and code standards follow you across tools. The format is simple markdown with YAML frontmatter. Any agent that supports skill loading can consume them.

The compound-engineering plugin adds what only a deep integration can: agents that spawn other agents, hooks that inject context, commands that orchestrate multi-step workflows. If you're in Claude Code, you get the full system. If you're elsewhere, you still get the discipline.

## Try it

```bash
# All skills (works everywhere)
npx skills add iliaal/ai-skills

# Just one skill
npx skills add iliaal/ai-skills -s code-review

# The full plugin (Claude Code)
claude plugins add iliaal/compound-engineering-plugin

# Convert the plugin for Codex
bun run src/index.ts install ./plugins/compound-engineering --to codex
```

The Codex converter transforms agents into skills, commands into prompts, and rewrites Claude Code syntax into Codex equivalents. It outputs a `.codex/` directory with everything mapped. The same CLI supports `--to opencode` and `--also` for multi-target conversion.

Both repos are MIT-licensed and on GitHub. The plugin ships weekly. The skills mirror syncs with every release.

Six months of daily use and weekly releases have taught me that AI agents don't lack capability. They lack process. Give them clear rules, verification gates, and escape hatches for when they're stuck, and the output quality jumps. That's what these projects encode, and they get a little better every week.
