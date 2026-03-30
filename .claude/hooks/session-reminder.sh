#!/usr/bin/env bash
# UserPromptSubmit hook — show available internal commands on first message.
# Outputs a reminder via hookSpecificOutput.message (displayed to user).

INPUT=$(cat)

# Only fire on the first user message (no parentUuid means first in chain)
# Check if this looks like the session's opening message by checking turn count
# Simple approach: only fire if the prompt is short (likely a greeting or first task)
# Better approach: use a state file to track if we've already shown the reminder

STATE_DIR="${HOME}/.claude/.hook-state"
mkdir -p "$STATE_DIR"

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATE_FILE="${STATE_DIR}/${SESSION_ID}.reminded"

# Already reminded this session
if [[ -f "$STATE_FILE" ]]; then
  exit 0
fi

# Mark as reminded
touch "$STATE_FILE"

# Clean up old state files (older than 7 days)
find "$STATE_DIR" -name "*.reminded" -mtime +7 -delete 2>/dev/null

# Output reminder
cat <<'REMINDER_EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "message": "Available commands: /sync-from-repos, /audit-plugin, /release, /announce, /analyze-misfires, /diagnose-negatives <skill>, /eval-skills, /evolve-skill <skill>"
  }
}
REMINDER_EOF
