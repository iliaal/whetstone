# Privacy policy

Whetstone does not collect, store, or transmit personal data, prompts, or source code to its author or any service the author operates. It contains no telemetry or analytics.

## Components that contact external services

| Component | Destination | What is sent | When |
|---|---|---|---|
| Context7 MCP server | `https://mcp.context7.com/mcp`, operated by Upstash | Library names and documentation search queries that Claude formulates | Only when Claude calls a Context7 tool |
| Optional Jev suggestions in the `subagent-start` hook | The service configured in your `jev` CLI | The subagent prompt and the names of already-selected skills | Only when you set `WHETSTONE_JEV=1` and have installed `jev`; off by default |
| `/ia-feature-video` upload step | Your own rclone remote and public base URL | The recorded video, preview GIF, and screenshots | Only when you have configured rclone and authorized the upload |
| `/ia-resolve-pr` and other GitHub-facing commands | GitHub, through your own `gh` CLI login | API requests for the pull request you name | Only when you run those commands |

Context7's handling of queries is governed by the [Context7 privacy policy](https://context7.com/privacy) and the [Upstash privacy policy](https://upstash.com/trust/privacy.pdf). Whetstone does not read or store any credential: `gh`, `rclone`, and `jev` use their own configuration.

## Local processing

The `inject-skills` PreToolUse hook matches each subagent prompt against local skill trigger patterns and briefly stores the prompt, agent type, and matched skill names in a local temporary queue at `${TMPDIR:-/tmp}/whetstone-subagent-queue-<uid>/<session_id>/`. Queue directories have mode `0700`; files have mode `0600`, readable and writable only by your user. The hook emits no output and does not change tool input or permissions.

The `subagent-start` hook claims the queued task for the same session and agent type and adds its recorded skill paths to the subagent's starting context; a record without stored matches is matched at start. When several tasks of the same agent type are queued together, each start receives the union of the group's skill paths, and the group's files are deleted once its last task is claimed; otherwise the claimed file is deleted immediately. Both hooks prune entries older than 15 minutes on each run, including entries from abandoned sessions. If neither hook runs again, expired files remain until the next run or system temp cleanup. A session retains at most 64 queued tasks. The hooks do not log prompt text elsewhere. Without Jev enabled, nothing leaves your machine.

## Contact

Report privacy questions or concerns as an issue at <https://github.com/iliaal/whetstone/issues>.
