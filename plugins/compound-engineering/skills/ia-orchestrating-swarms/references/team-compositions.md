# Preset Team Compositions

Start here before designing a custom team. Each preset is a proven shape for a specific work pattern — use the smallest preset that covers all required dimensions. Adding teammates beyond what the work needs adds coordination overhead without speedup.

| Preset | Size | Agents | Use when |
|--------|------|--------|----------|
| Review Team | 3 | 3x reviewers on distinct dimensions (security, performance, architecture) | Code changes need multi-dimensional quality assessment |
| Debug Team | 3 | 3x investigators, one per competing hypothesis | Bug has multiple plausible root causes |
| Feature Team | 3 | 1x lead + 2x implementers with exclusive file ownership | Feature decomposes into parallel work streams |
| Fullstack Team | 4 | 1x lead + frontend impl + backend impl + test impl | Feature spans frontend, backend, and test layers |
| Migration Team | 4 | 1x lead + 2x implementers + 1x reviewer | Large codebase migration needing parallel work with correctness verification |
| Security Team | 4 | 4x reviewers on OWASP / auth / dependencies / secrets | Comprehensive security audit across multiple attack surfaces |
| Research Team | 3 | 3x read-only researchers (`Explore` or `general-purpose`), each on a distinct question | Codebase exploration, library comparisons, parallel research |

## Sizing discipline

Two reviewers flagging the same issues means the dimensions overlap. Redefine each focus area instead of adding more agents. Four agents doing six independent tasks are usually worse than three agents covering two tasks each — coordination overhead scales non-linearly.

## Cardinal `subagent_type` rule

Read-only agent types (`Explore`, `Plan`) cannot modify files. Never assign implementation tasks to read-only agents — the spawn will silently succeed while writes fail. For any task that creates or edits files, use `general-purpose` or a specialized writable agent type.

| subagent_type | Tools | Use for |
|---------------|-------|---------|
| `general-purpose` | All tools (Read, Write, Edit, Bash, ...) | Implementation, debugging, anything that modifies files |
| `Explore` | Read-only (Read, Grep, Glob) | Research, codebase search, analysis — NEVER implementation |
| `Plan` | Read-only | Architecture planning, task decomposition — NEVER implementation |

## Custom team guidelines

When building a team that doesn't match a preset:

1. **Every team needs a coordinator** — either designate a lead or have the orchestrator coordinate directly
2. **Match roles to writable agent types** — read-only types cannot implement
3. **Avoid duplicate roles** — two agents doing the same thing wastes resources
4. **Define file ownership upfront** — each teammate needs exclusive write ownership of specific files
5. **Keep it small** — 2-4 teammates is the sweet spot; 5+ requires significant coordination overhead
