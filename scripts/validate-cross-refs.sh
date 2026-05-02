#!/usr/bin/env bash
set -Eeuo pipefail

# Validate that agents, commands, and skills don't reference nonexistent components.
# Checks for broken references to agents/, commands/, and skills/ within plugin files.
#
# Usage: bash scripts/validate-cross-refs.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugins/whetstone"

errors=0

# Strip fenced code blocks from a file before scanning for references.
# This prevents false positives from example/illustrative code.
strip_code_blocks() {
    sed '/^```/,/^```/d' "$1"
}

# --- Build inventories ---

declare -A known_agents
while IFS= read -r f; do
    name=$(basename "$f" .md)
    known_agents["$name"]=1
done < <(find "$PLUGIN_DIR/agents" -name "*.md" -type f 2>/dev/null)

declare -A known_commands
while IFS= read -r f; do
    name=$(basename "$f" .md)
    known_commands["$name"]=1
done < <(find "$PLUGIN_DIR/commands" -name "*.md" -type f 2>/dev/null)

declare -A known_skills
while IFS= read -r d; do
    name=$(basename "$d")
    known_skills["$name"]=1
done < <(find "$PLUGIN_DIR/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

# --- Check references in commands ---

echo "Checking command files for broken references..."
while IFS= read -r cmd_file; do
    cmd_name=$(basename "$cmd_file" .md)

    content=$(strip_code_blocks "$cmd_file")

    # Check agent references: agents/category/name.md
    while IFS= read -r ref; do
        agent_name=$(echo "$ref" | grep -oP 'agents/[^/]+/\K[^.]+' 2>/dev/null || true)
        if [[ -n "$agent_name" && -z "${known_agents[$agent_name]:-}" ]]; then
            echo "  ERROR: commands/$cmd_name.md references unknown agent: $agent_name"
            ((errors++))
        fi
    done < <(echo "$content" | grep -oP 'agents/\S+\.md' 2>/dev/null || true)

    # Check skill references: skills/name/ or skills/name/SKILL.md
    while IFS= read -r ref; do
        skill_name=$(echo "$ref" | grep -oP 'skills/\K[^/]+' 2>/dev/null || true)
        if [[ -n "$skill_name" && -z "${known_skills[$skill_name]:-}" ]]; then
            echo "  ERROR: commands/$cmd_name.md references unknown skill: $skill_name"
            ((errors++))
        fi
    done < <(echo "$content" | grep -oP 'skills/[a-z][a-z0-9-]+' 2>/dev/null || true)

done < <(find "$PLUGIN_DIR/commands" -name "*.md" -type f 2>/dev/null)

# --- Check references in agents ---

echo "Checking agent files for broken references..."
while IFS= read -r agent_file; do
    agent_name=$(basename "$agent_file" .md)

    content=$(strip_code_blocks "$agent_file")

    # Check skill references
    while IFS= read -r ref; do
        skill_name=$(echo "$ref" | grep -oP 'skills/\K[^/]+' 2>/dev/null || true)
        if [[ -n "$skill_name" && -z "${known_skills[$skill_name]:-}" ]]; then
            echo "  ERROR: agents/.../$agent_name.md references unknown skill: $skill_name"
            ((errors++))
        fi
    done < <(echo "$content" | grep -oP 'skills/[a-z][a-z0-9-]+' 2>/dev/null || true)

done < <(find "$PLUGIN_DIR/agents" -name "*.md" -type f 2>/dev/null)

# --- Check references in skills ---

echo "Checking skill files for broken references..."
while IFS= read -r skill_file; do
    skill_dir=$(dirname "$skill_file")
    skill_name=$(basename "$skill_dir")

    # Check for references/ files that don't exist
    while IFS= read -r ref; do
        ref_path="$skill_dir/$ref"
        if [[ ! -f "$ref_path" ]]; then
            echo "  ERROR: skills/$skill_name/SKILL.md links to missing file: $ref"
            ((errors++))
        fi
    done < <(grep -oP '\]\(\./references/[^)]+\)' "$skill_file" 2>/dev/null | grep -oP '\./references/[^)]+' || true)

    # Check for scripts/ files that don't exist
    while IFS= read -r ref; do
        ref_path="$skill_dir/$ref"
        if [[ ! -f "$ref_path" ]]; then
            echo "  ERROR: skills/$skill_name/SKILL.md links to missing file: $ref"
            ((errors++))
        fi
    done < <(grep -oP '\]\(\./scripts/[^)]+\)' "$skill_file" 2>/dev/null | grep -oP '\./scripts/[^)]+' || true)

done < <(find "$PLUGIN_DIR/skills" -name "SKILL.md" -type f 2>/dev/null)

# --- Check README table entries ---

echo "Checking README tables for broken links..."
readme="$PLUGIN_DIR/README.md"
if [[ -f "$readme" ]]; then
    # Check agent links in README
    while IFS= read -r ref; do
        if [[ ! -f "$PLUGIN_DIR/$ref" ]]; then
            echo "  ERROR: README.md links to missing file: $ref"
            ((errors++))
        fi
    done < <(grep -oP 'agents/[^)]+\.md' "$readme" 2>/dev/null || true)

    # Check skill links in README
    while IFS= read -r ref; do
        if [[ ! -f "$PLUGIN_DIR/$ref" ]]; then
            echo "  ERROR: README.md links to missing file: $ref"
            ((errors++))
        fi
    done < <(grep -oP 'skills/[^)]+/SKILL\.md' "$readme" 2>/dev/null || true)

    # Check command links in README
    while IFS= read -r ref; do
        if [[ ! -f "$PLUGIN_DIR/$ref" ]]; then
            echo "  ERROR: README.md links to missing file: $ref"
            ((errors++))
        fi
    done < <(grep -oP 'commands/[^)]+\.md' "$readme" 2>/dev/null || true)
fi

# --- Summary ---

echo ""
if [[ "$errors" -gt 0 ]]; then
    echo "FAILED: $errors broken reference(s) found."
    exit 1
else
    echo "OK: All cross-references valid."
    echo "  Agents:   ${#known_agents[@]}"
    echo "  Commands: ${#known_commands[@]}"
    echo "  Skills:   ${#known_skills[@]}"
fi
