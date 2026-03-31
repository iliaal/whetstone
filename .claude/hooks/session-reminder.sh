#!/usr/bin/env bash
# UserPromptSubmit hook — show available internal commands on first message.

INPUT=$(cat)

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATE_DIR="${HOME}/.claude/.hook-state"
mkdir -p "$STATE_DIR"
STATE_FILE="${STATE_DIR}/${SESSION_ID}.reminded"

# Already reminded this session
if [[ -f "$STATE_FILE" ]]; then
  exit 0
fi

# Mark as reminded
touch "$STATE_FILE"

# Clean up old state files (older than 7 days)
find "$STATE_DIR" -name "*.reminded" -mtime +7 -delete 2>/dev/null

# Output additionalContext at top level (no hookSpecificOutput wrapper)
cat <<'EOF'
{
  "additionalContext": "<session-commands>Available internal commands for this project: /sync-from-repos, /audit-plugin, /release, /announce, /analyze-misfires, /diagnose-negatives <skill>, /eval-skills, /evolve-skill <skill></session-commands>"
}
EOF
