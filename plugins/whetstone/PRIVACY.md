# Privacy policy

Whetstone does not collect, store, or transmit personal data, prompts, or source code to its author or any service the author operates. It contains no telemetry or analytics.

## Components that contact external services

| Component | Destination | What is sent | When |
|---|---|---|---|
| Context7 MCP server | `https://mcp.context7.com/mcp`, operated by Upstash | Library names and documentation search queries that Claude formulates | Only when Claude calls a Context7 tool |
| Optional Jev suggestions in the `inject-skills` hook | The service configured in your `jev` CLI | The subagent prompt and the names of already-selected skills | Only when you set `WHETSTONE_JEV=1` and have installed `jev`; off by default |
| `/ia-feature-video` upload step | Your own rclone remote and public base URL | The recorded video, preview GIF, and screenshots | Only when you have configured rclone and authorized the upload |
| `/ia-resolve-pr` and other GitHub-facing commands | GitHub, through your own `gh` CLI login | API requests for the pull request you name | Only when you run those commands |

Context7's handling of queries is governed by the [Context7 privacy policy](https://context7.com/privacy) and the [Upstash privacy policy](https://upstash.com/trust/privacy.pdf). Whetstone does not read or store any credential: `gh`, `rclone`, and `jev` use their own configuration.

## Local processing

The `inject-skills` hook runs locally. It matches subagent prompts against skill trigger patterns on your machine and adds the matching skill instructions to the subagent prompt. Without Jev enabled, nothing leaves your machine.

## Contact

Report privacy questions or concerns as an issue at <https://github.com/iliaal/whetstone/issues>.
