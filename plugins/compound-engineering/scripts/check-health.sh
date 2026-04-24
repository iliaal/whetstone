#!/usr/bin/env bash
# Compound Engineering environment health check
# Outputs a formatted diagnostic report in one pass.

set -o pipefail

# =====================================================
#  Dependency config
# =====================================================
# Format: name|alt|tier|install_apt|install_brew|url
#   name        -- primary command to probe with `command -v`
#   alt         -- alternative command name (checked if name absent); empty if none
#   tier        -- recommended (counted toward issues) | optional (info only)
#   install_apt -- apt-compatible install command (empty if not available via apt)
#   install_brew-- brew install command (empty if not available via brew)
#   url         -- upstream project URL (always shown as fallback)
# To add a dependency: append one line. No other changes needed.

deps=(
  # Core -- required for the release pipeline and core workflows
  "git||recommended|sudo apt install -y git|brew install git|https://git-scm.com/downloads"
  "gh||recommended|https://github.com/cli/cli/blob/trunk/docs/install_linux.md|brew install gh|https://cli.github.com"
  "jq||recommended|sudo apt install -y jq|brew install jq|https://jqlang.github.io/jq/"
  "python3|python|recommended|sudo apt install -y python3|brew install python@3|https://www.python.org/downloads/"
  "claude||recommended|npm install -g @anthropic-ai/claude-code|npm install -g @anthropic-ai/claude-code|https://claude.com/claude-code"
  # Optional -- Node toolchain (needed to install claude CLI and run skills CLI)
  "node||optional|sudo apt install -y nodejs|brew install node|https://nodejs.org"
  "npm||optional|sudo apt install -y npm|brew install node|https://nodejs.org"
  # Optional -- Codex cycle workflow
  "codex||optional|npm install -g @openai/codex|npm install -g @openai/codex|https://github.com/openai/codex"
  # Optional -- /announce + post-thread.py
  "playwright||optional|pip install playwright && playwright install|pip install playwright && playwright install|https://playwright.dev/python"
  "edge-cdp||optional|pip install edge-cdp|pip install edge-cdp|https://pypi.org/project/edge-cdp"
)

# =====================================================
#  Args
# =====================================================

plugin_version=""
while [ $# -gt 0 ]; do
  case "$1" in
    --version) [ -n "${2:-}" ] && plugin_version="$2" && shift 2 || shift ;;
    *) shift ;;
  esac
done

# =====================================================
#  Helpers
# =====================================================

ok()      { echo "  🟢  $1"; }
warn()    { echo "  🟡  $1"; }
detail()  { echo "       $1"; }
section() { echo ""; echo " $1"; }

has_apt=$(command -v apt-get >/dev/null 2>&1 && echo "yes" || echo "no")
has_brew=$(command -v brew >/dev/null 2>&1 && echo "yes" || echo "no")
in_repo=$(git rev-parse --is-inside-work-tree >/dev/null 2>&1 && echo "yes" || echo "no")

# =====================================================
#  Check tools
# =====================================================

rec_ok=0; rec_total=0; opt_ok=0; opt_total=0; issues=0
results=()

for entry in "${deps[@]}"; do
  IFS='|' read -r name alt tier install_apt install_brew url <<< "$entry"

  resolved=""
  if command -v "$name" >/dev/null 2>&1; then
    resolved="$name"
  elif [ -n "$alt" ] && command -v "$alt" >/dev/null 2>&1; then
    resolved="$alt"
  fi

  if [ "$tier" = "optional" ]; then
    opt_total=$((opt_total + 1))
    [ -n "$resolved" ] && opt_ok=$((opt_ok + 1))
  else
    rec_total=$((rec_total + 1))
    [ -n "$resolved" ] && rec_ok=$((rec_ok + 1))
  fi

  if [ -n "$resolved" ]; then
    results+=("$name|$resolved|$tier|ok|$install_apt|$install_brew|$url")
  else
    results+=("$name|$alt|$tier|missing|$install_apt|$install_brew|$url")
  fi
done

# =====================================================
#  Output
# =====================================================

echo ""
if [ -n "$plugin_version" ]; then
  ok "Plugin version v${plugin_version}"
fi

section "Tools  ${rec_ok}/${rec_total} required, ${opt_ok}/${opt_total} optional"

render_row() {
  local tier="$1"
  for result in "${results[@]}"; do
    IFS='|' read -r name resolved row_tier status install_apt install_brew url <<< "$result"
    [ "$row_tier" = "$tier" ] || continue
    if [ "$status" = "ok" ]; then
      if [ "$resolved" != "$name" ]; then
        ok "$name (found as: $resolved)"
      else
        ok "$name"
      fi
    else
      if [ "$tier" = "optional" ]; then
        warn "$name (optional)"
      else
        warn "$name"
        issues=$((issues + 1))
      fi
      if [ "$has_apt" = "yes" ] && [ -n "$install_apt" ]; then
        detail "$install_apt"
      elif [ "$has_brew" = "yes" ] && [ -n "$install_brew" ]; then
        detail "$install_brew"
      fi
      detail "$url"
    fi
  done
}

render_row "recommended"
if [ "$opt_total" -gt 0 ]; then
  echo ""
  render_row "optional"
fi

# =====================================================
#  Project check (repo only)
# =====================================================

if [ "$in_repo" = "yes" ]; then
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -f "$repo_root/compound-engineering.local.md" ]; then
    section "Project"
    ok "compound-engineering.local.md present (review agents configured)"
  fi
fi

# =====================================================
#  Bottom line
# =====================================================

echo ""
if [ "$issues" -eq 0 ]; then
  echo " ✅  All clear  ${rec_ok}/${rec_total} required  ${opt_ok}/${opt_total} optional"
else
  echo " ⚠️   ${issues} issue(s) found  ${rec_ok}/${rec_total} required  ${opt_ok}/${opt_total} optional"
fi
echo ""
