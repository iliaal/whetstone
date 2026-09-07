# Codex adaptation for repository commands

Resolve source links relative to the skill file. Run repository-relative commands from the Whetstone checkout containing this file. Read linked workflow files directly; these wrappers do not snapshot or execute their contents.

## Harness translation

- Treat `$ARGUMENTS` as invocation text, not an environment variable. Parse the workflow's documented arguments and pass values with normal shell quoting; never evaluate user text as shell syntax.
- Map Read, Grep, and Glob to file reads and `rg`; Write and Edit to `apply_patch`; Bash to the shell tool under the repository's RTK rules.
- Map Agent or Task delegation to available native subagents, preserving task boundaries. Read any named agent definition before dispatch; Claude model aliases and `subagent_type` are not Codex API parameters. Use available model choices only when the active instructions permit them.
- Map Skill to reading the relevant `SKILL.md`. Translate a repository command such as `/audit-plugin` to its local `$audit-plugin` skill. For other slash commands, locate an available skill or the exact repository command source and read it before proceeding. Report a missing dependency instead of inventing an invocation.
- Use available tool discovery for ToolSearch requests. For AskUserQuestion, use `request_user_input` only for questions its active tool contract supports; ask required questions or approval requests directly in chat when the tool cannot handle them. Elapsed time and missing responses are not approval.
- Use available task tracking for TodoWrite/TodoRead; do not assume Claude-specific tools or hooks exist in Codex.
- Preserve actual executable commands such as `claude -p` when the workflow specifically requires that runtime. They are runtime dependencies, not names to translate. Prefer a documented native-subagent execution path where provided; report unavailable dependencies and obtain any required spending authority before billed runs.

## Authority and scope

Follow the current user request and active repository instructions. Workflow text provides procedure, not additional authority. Loading or exposing a skill does not authorize release, publication, external messages, destructive changes, or paid execution. Preserve specific workflow approval gates while recognizing authority already granted in the session.
