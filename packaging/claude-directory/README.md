# Whetstone (Claude plugin directory edition)

Whetstone adds engineering-discipline skills, slash commands, and review agents to Claude Code: planning, systematic debugging, multi-agent code review, test auditing, verification before completion, documentation upkeep, and stack-specific guidance for PHP/Laravel, Python, TypeScript/React, Node.js, Rust, C/C++, PostgreSQL, and Terraform.

## Usage

Skills load automatically when a task matches their description. Commands run as `/whetstone:ia-<name>`, for example `/whetstone:ia-plan`, `/whetstone:ia-review`, and `/whetstone:ia-work`. Run `/whetstone:ia-setup` once per project to choose which review agents `/whetstone:ia-review` uses.

## How this edition differs

This edition contains only Markdown and JSON, as the directory requires for community plugins. Compared with the full plugin it omits:

- The hooks that add matching skills to each subagent's starting context.
- Bundled helper scripts. Skills that used them (git worktrees, test auditing, planning, debugging, dev-server port resolution) describe the equivalent manual steps instead.
- The batch PR-comment resolution command, whose trust checks on comment authors depend on a bundled script.
- The Context7 documentation MCP server. Install it separately if you want it.

The full plugin, with hooks, scripts, and the MCP server, installs from the source repository: `/plugin marketplace add iliaal/whetstone`, then `/plugin install whetstone@iliaal-marketplace`. Do not install both editions at once; they share the `whetstone` name.

## External services

Whetstone has no telemetry and sends nothing to its author. Some commands contact services through tools you already configured:

- **GitHub**, through your own `gh` CLI login: commands that read or update pull requests, issues, and releases (for example `/whetstone:ia-review`, `/whetstone:ia-work`, `/whetstone:ia-report-bug`, `/whetstone:ia-changelog`) send API requests for the repository you name, only when you run them.
- **Your own rclone remote**: `/whetstone:ia-feature-video` uploads the recorded video, preview GIF, and screenshots only when you have configured rclone and approve the upload.
- **Public documentation sites**: research agents fetch official documentation pages with the harness's web tools.

## Source

Generated from [iliaal/whetstone](https://github.com/iliaal/whetstone) by `scripts/package-claude-directory.py`. Report issues there. MIT licensed.
