#!/usr/bin/env bash
set -Eeuo pipefail

# Update plugin.json and marketplace.json descriptions with current component counts.
# Called by bundle-skills.sh automatically, but can also be run standalone after
# adding/removing agents, commands, skills, hooks, or MCP servers.
#
# Usage:
#   bash scripts/update-metadata.sh             # rewrite descriptions in place
#   bash scripts/update-metadata.sh --dry-run   # print counts, make no changes
#   bash scripts/update-metadata.sh --check     # fail (exit 1) if committed metadata
#                                               # is out of sync with current counts,
#                                               # or if the two version fields diverge.
#
# --check is a /release pre-commit gate: it re-renders the count-derived
# descriptions and byte-compares them against what is committed, so a hand-edit
# to either JSON (or a component added without re-running this script) is caught
# loudly instead of shipping stale counts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugins/whetstone"
SKILLS_DIR="$PLUGIN_DIR/skills"
PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"

MODE="write"
case "${1:-}" in
    --dry-run) MODE="dry-run" ;;
    --check)   MODE="check" ;;
    "")        MODE="write" ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
esac

# --- Count components ---

agent_count=$(find "$PLUGIN_DIR/agents" -name "*.md" -type f -not -path "*/references/*" | wc -l)
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

# --- Render the canonical description strings (single source of truth) ---

desc="AI-powered development tools. ${agent_count} agents, ${command_count} commands, ${skill_count} skills, ${hook_fragment}${mcp_count} MCP server for code review, research, design, and workflow automation."
mkt_desc="AI-powered development tools that get smarter with every use. Make each unit of engineering work easier than the last. Includes ${agent_count} specialized agents, ${command_count} commands, ${skill_count} skills, and ${hook_fragment}${mcp_count} MCP server."

# --- Mode: check (drift gate, no writes) ---

if [[ "$MODE" == check ]]; then
    drift=0

    cur_desc=$(jq -r '.description' "$PLUGIN_JSON")
    cur_mkt_desc=$(jq -r '.plugins[0].description' "$MARKETPLACE_JSON")

    if [[ "$cur_desc" != "$desc" ]]; then
        echo "DRIFT: plugins/whetstone/.claude-plugin/plugin.json description out of sync." >&2
        echo "  expected: $desc" >&2
        echo "  actual:   $cur_desc" >&2
        drift=1
    fi
    if [[ "$cur_mkt_desc" != "$mkt_desc" ]]; then
        echo "DRIFT: .claude-plugin/marketplace.json description out of sync." >&2
        echo "  expected: $mkt_desc" >&2
        echo "  actual:   $cur_mkt_desc" >&2
        drift=1
    fi

    # Version fields must agree across the two distribution files.
    plugin_ver=$(jq -r '.version' "$PLUGIN_JSON")
    mkt_ver=$(jq -r '.plugins[0].version // .metadata.version // empty' "$MARKETPLACE_JSON")
    if [[ -n "$mkt_ver" && "$plugin_ver" != "$mkt_ver" ]]; then
        echo "DRIFT: version mismatch plugin.json ($plugin_ver) != marketplace.json ($mkt_ver)." >&2
        drift=1
    fi

    if [[ "$drift" -ne 0 ]]; then
        echo "" >&2
        echo "Run 'bash scripts/update-metadata.sh' to regenerate, then commit the result." >&2
        exit 1
    fi
    echo "OK: metadata in sync (counts and version)."
    exit 0
fi

# --- Mode: write ---

if [[ "$MODE" == write ]]; then
    tmp=$(mktemp)
    jq --arg d "$desc" '.description = $d' "$PLUGIN_JSON" > "$tmp"
    mv "$tmp" "$PLUGIN_JSON"

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

if [[ "$MODE" == dry-run ]]; then
    printf "\n  (dry run — no changes made)\n"
fi
