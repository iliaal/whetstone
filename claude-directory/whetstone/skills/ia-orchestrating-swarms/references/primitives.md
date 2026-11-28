# Orchestration Primitives

Glossary and file-structure reference. Load when onboarding to the team/teammate/task model or debugging paths.

## Primitives

| Primitive | What It Is |
|-----------|-----------|
| **Agent** | A Claude instance that can use tools. You are an agent. Subagents are agents you spawn. |
| **Team** | A session-managed group of agents. One leader, multiple teammates. Config: `~/.claude/teams/{name}/config.json`; use the runtime's session-derived name. |
| **Teammate** | A named agent launched through `Agent` in an interactive Claude session with teams enabled. Communicates through `SendMessage`. |
| **Leader** | The session coordinating assigned work and teammate lifecycle. Automatic protocol transitions do not establish review or user consent. |
| **Task** | A work item with subject, description, status, owner, and dependencies. Stored: `~/.claude/tasks/{team}/N.json` |
| **Inbox** | JSON file where an agent receives messages from teammates. Path: `~/.claude/teams/{name}/inboxes/{agent}.json` |
| **Message** | A JSON object sent between agents. Can be text or structured (shutdown_request, idle_notification, etc). |
| **Backend** | How teammates run: `in-process`, `tmux`, or `iterm2`, selected through supported settings. See [spawn-backends.md](./spawn-backends.md). |

## Core File Layout

```
~/.claude/teams/{team-name}/
├── config.json              # Team metadata and member list
└── inboxes/
    ├── team-lead.json       # Leader's inbox
    └── worker-1.json        # Worker inbox

~/.claude/tasks/{team-name}/
├── 1.json                   # Task #1
└── 2.json                   # Task #2
```
