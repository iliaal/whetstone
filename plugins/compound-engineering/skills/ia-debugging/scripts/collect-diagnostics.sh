#!/usr/bin/env bash
# collect-diagnostics.sh — Gather environment diagnostics for debugging
# Usage: bash collect-diagnostics.sh [output-file]
#
# Collects system info, language versions, git state, and project metadata.
# Outputs structured report to stdout or optional file.

set -euo pipefail

OUTPUT="${1:-}"

collect() {
    local buf=""

    buf+="# Diagnostic Report"$'\n'
    buf+="**Collected:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"$'\n\n'

    # --- System ---
    buf+="## System"$'\n\n'
    buf+="| Property | Value |"$'\n'
    buf+="|----------|-------|"$'\n'
    buf+="| OS | $(uname -s) $(uname -r) |"$'\n'
    buf+="| Arch | $(uname -m) |"$'\n'
    buf+="| Shell | ${SHELL:-unknown} |"$'\n'
    if command -v bash &>/dev/null; then
        buf+="| Bash | $(bash --version | head -1) |"$'\n'
    fi
    buf+="| User | $(whoami) |"$'\n'
    buf+="| PWD | $(pwd) |"$'\n'
    buf+=$'\n'

    # --- Disk / Memory ---
    buf+="## Resources"$'\n\n'
    buf+='```'$'\n'
    buf+="Disk (pwd): $(df -h . 2>/dev/null | tail -1 | awk '{print $4 " available of " $2}')"$'\n'
    if command -v free &>/dev/null; then
        buf+="Memory: $(free -h 2>/dev/null | awk '/^Mem:/{print $7 " available of " $2}')"$'\n'
    fi
    buf+='```'$'\n\n'

    # --- Git ---
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        buf+="## Git"$'\n\n'
        buf+="| Property | Value |"$'\n'
        buf+="|----------|-------|"$'\n'
        buf+="| Branch | $(git branch --show-current 2>/dev/null || echo 'detached') |"$'\n'
        buf+="| Last commit | $(git log -1 --format='%h %s' 2>/dev/null || echo 'none') |"$'\n'
        buf+="| Dirty files | $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') |"$'\n'
        buf+="| Remote | $(git remote get-url origin 2>/dev/null || echo 'none') |"$'\n'
        buf+=$'\n'
    fi

    # --- Language Versions ---
    buf+="## Languages & Runtimes"$'\n\n'
    buf+="| Tool | Version |"$'\n'
    buf+="|------|---------|"$'\n'
    for cmd in node python python3 php ruby go java rustc; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            case "$cmd" in
                node)    ver=$("$cmd" --version 2>/dev/null) ;;
                python|python3) ver=$("$cmd" --version 2>/dev/null) ;;
                php)     ver=$("$cmd" --version 2>/dev/null | head -1) ;;
                ruby)    ver=$("$cmd" --version 2>/dev/null) ;;
                go)      ver=$("$cmd" version 2>/dev/null) ;;
                java)    ver=$("$cmd" -version 2>&1 | head -1) ;;
                rustc)   ver=$("$cmd" --version 2>/dev/null) ;;
                *)       ver="installed" ;;
            esac
            buf+="| ${cmd} | ${ver} |"$'\n'
        fi
    done
    buf+=$'\n'

    # --- Package Managers ---
    buf+="## Package Managers"$'\n\n'
    buf+="| Tool | Version |"$'\n'
    buf+="|------|---------|"$'\n'
    for cmd in npm pnpm yarn bun pip uv composer cargo bundler gem; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" --version 2>/dev/null | head -1) || ver="installed"
            buf+="| ${cmd} | ${ver} |"$'\n'
        fi
    done
    buf+=$'\n'

    # --- Project Detection ---
    buf+="## Project Files Detected"$'\n\n'
    for f in package.json composer.json pyproject.toml Cargo.toml Gemfile go.mod build.gradle pom.xml Makefile Dockerfile docker-compose.yml .env.example; do
        if [ -f "$f" ]; then
            buf+="- \`${f}\`"$'\n'
        fi
    done
    buf+=$'\n'

    # --- Environment Variables (safe subset) ---
    buf+="## Environment (safe subset)"$'\n\n'
    buf+="| Variable | Value |"$'\n'
    buf+="|----------|-------|"$'\n'
    for var in NODE_ENV APP_ENV RAILS_ENV FLASK_ENV ENVIRONMENT CI TERM; do
        local val="${!var:-}"
        if [ -n "$val" ]; then
            buf+="| ${var} | ${val} |"$'\n'
        fi
    done
    buf+=$'\n'

    echo "$buf"
}

report=$(collect)

if [ -n "$OUTPUT" ]; then
    echo "$report" > "$OUTPUT"
    echo "Diagnostics written to ${OUTPUT}"
else
    echo "$report"
fi
