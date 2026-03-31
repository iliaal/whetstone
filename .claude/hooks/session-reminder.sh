#!/usr/bin/env bash
# SessionStart hook — show available internal commands at session start.

cat <<'EOF'
{
  "additionalContext": "<session-commands>Available internal commands for this project: /sync-from-repos, /audit-plugin, /release, /announce, /analyze-misfires, /diagnose-negatives <skill>, /eval-skills, /evolve-skill <skill></session-commands>"
}
EOF
