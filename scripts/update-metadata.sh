#!/usr/bin/env bash
set -Eeuo pipefail

# Update plugin.json and marketplace.json descriptions with current component counts.
# Called by bundle-skills.sh automatically, but can also be run standalone after
# adding/removing agents, commands, skills, hooks, or MCP servers.
#
# Usage: bash scripts/update-metadata.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugins/compound-engineering"
SKILLS_DIR="$PLUGIN_DIR/skills"
PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# --- Count components ---

agent_count=$(find "$PLUGIN_DIR/agents" -name "*.md" -type f | wc -l)
command_count=$(find "$PLUGIN_DIR/commands" -name "*.md" -type f -not -path "*/references/*" | wc -l)
skill_count=$(find "$SKILLS_DIR" -name "SKILL.md" -type f | wc -l)
hook_count=0
if [[ -f "$PLUGIN_DIR/hooks/hooks.json" ]]; then
    hook_count=$(jq '[.hooks[][] | .hooks | length] | add // 0' "$PLUGIN_DIR/hooks/hooks.json")
fi
mcp_count=$(jq '.mcpServers | length' "$PLUGIN_JSON")

# Build optional fragments for descriptions
hook_fragment=""
[[ "$hook_count" -gt 0 ]] && hook_fragment="${hook_count} hook, "

# --- Update metadata ---

if [[ "$DRY_RUN" == false ]]; then
    # Update plugin.json description
    desc="AI-powered development tools. ${agent_count} agents, ${command_count} commands, ${skill_count} skills, ${hook_fragment}${mcp_count} MCP server for code review, research, design, and workflow automation."
    tmp=$(mktemp)
    jq --arg d "$desc" '.description = $d' "$PLUGIN_JSON" > "$tmp"
    mv "$tmp" "$PLUGIN_JSON"

    # Update marketplace.json plugin description
    mkt_desc="AI-powered development tools that get smarter with every use. Make each unit of engineering work easier than the last. Includes ${agent_count} specialized agents, ${command_count} commands, ${skill_count} skills, and ${hook_fragment}${mcp_count} MCP server."
    tmp=$(mktemp)
    jq --arg d "$mkt_desc" '.plugins[0].description = $d' "$MARKETPLACE_JSON" > "$tmp"
    mv "$tmp" "$MARKETPLACE_JSON"

    # Validate JSON
    jq . "$PLUGIN_JSON" > /dev/null
    jq . "$MARKETPLACE_JSON" > /dev/null
fi

# --- Summary ---

printf "  Agents:   %d\n" "$agent_count"
printf "  Commands: %d\n" "$command_count"
printf "  Skills:   %d\n" "$skill_count"
printf "  Hooks:    %d\n" "$hook_count"
printf "  MCP:      %d\n" "$mcp_count"

if [[ "$DRY_RUN" == true ]]; then
    printf "\n  (dry run — no changes made)\n"
fi
