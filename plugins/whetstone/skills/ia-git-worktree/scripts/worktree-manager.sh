#!/bin/bash

# Git Worktree Manager
# Handles creating, listing, switching, and cleaning up Git worktrees
# KISS principle: Simple, interactive, opinionated

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get repo root
CURRENT_ROOT=$(git rev-parse --show-toplevel)
COMMON_DIR=$(realpath -- "$(git rev-parse --git-common-dir)")
CURRENT_GIT_DIR=$(realpath -- "$(git rev-parse --git-dir)")
if [[ "$CURRENT_GIT_DIR" == "$COMMON_DIR" ]]; then
  GIT_ROOT="$CURRENT_ROOT"
elif [[ -f "$COMMON_DIR/whetstone-main-root" ]]; then
  IFS= read -r GIT_ROOT < "$COMMON_DIR/whetstone-main-root"
else
  IFS= read -r main_record < <(git worktree list --porcelain)
  GIT_ROOT=${main_record#worktree }
fi
[[ "$(git -C "$GIT_ROOT" rev-parse --show-toplevel)" == "$GIT_ROOT" ]] || {
  echo "Error: main checkout unavailable; run create from the main checkout first" >&2
  exit 1
}
ROOT_COMMON_DIR=$(git -C "$GIT_ROOT" rev-parse --git-common-dir)
if [[ "$ROOT_COMMON_DIR" != /* ]]; then
  ROOT_COMMON_DIR="$GIT_ROOT/$ROOT_COMMON_DIR"
fi
[[ "$(realpath -- "$ROOT_COMMON_DIR")" == "$COMMON_DIR" ]] || {
  echo "Error: cannot resolve the main worktree safely" >&2
  exit 1
}
WORKTREE_DIR="$GIT_ROOT/.worktrees"

resolve_worktree() {
  local name="$1" candidate registered
  git check-ref-format --branch "$name" >/dev/null 2>&1 || return 1
  candidate=$(realpath -e -- "$WORKTREE_DIR/$name") || return 1
  [[ "$candidate" == "$WORKTREE_DIR/"* ]] || return 1
  while IFS= read -r registered; do
    if [[ "$registered" == "worktree $candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(git worktree list --porcelain)
  return 1
}

# Ensure .worktrees is in .gitignore
ensure_gitignore() {
  if ! grep -q "^\.worktrees$" "$GIT_ROOT/.gitignore" 2>/dev/null; then
    echo ".worktrees" >> "$GIT_ROOT/.gitignore"
  fi
}

# Copy .env files from main repo to worktree
copy_env_files() {
  local worktree_path="$1"

  echo -e "${BLUE}Copying environment files...${NC}"

  # Find all .env* files in root (excluding .env.example which should be in git)
  local env_files=()
  for f in "$GIT_ROOT"/.env*; do
    if [[ -f "$f" ]]; then
      local basename
      basename=$(basename "$f")
      # Skip .env.example (that's typically committed to git)
      if [[ "$basename" != ".env.example" ]]; then
        env_files+=("$basename")
      fi
    fi
  done

  if [[ ${#env_files[@]} -eq 0 ]]; then
    echo -e "  ${YELLOW}ℹ️  No .env files found in main repository${NC}"
    return
  fi

  local copied=0
  for env_file in "${env_files[@]}"; do
    local source="$GIT_ROOT/$env_file"
    local dest="$worktree_path/$env_file"

    if [[ -f "$dest" ]]; then
      echo -e "  ${YELLOW}⚠️  $env_file already exists, backing up to ${env_file}.backup${NC}"
      cp "$dest" "${dest}.backup"
    fi

    cp "$source" "$dest"
    echo -e "  ${GREEN}✓ Copied $env_file${NC}"
    copied=$((copied + 1))
  done

  echo -e "  ${GREEN}✓ Copied $copied environment file(s)${NC}"
}

# Create a new worktree
create_worktree() {
  local branch_name="$1"
  local from_branch="${2:-main}"

  if [[ -z "$branch_name" ]]; then
    echo -e "${RED}Error: Branch name required${NC}"
    exit 1
  fi

  git check-ref-format --branch "$branch_name" >/dev/null || return 1
  if [[ -L "$WORKTREE_DIR" ]]; then
    echo "Error: refusing a symlinked worktree directory" >&2
    return 1
  fi

  local worktree_path="$WORKTREE_DIR/$branch_name"
  if [[ "$(realpath -m -- "$worktree_path")" != "$worktree_path" ]]; then
    echo "Error: refusing redirected worktree path: $worktree_path" >&2
    return 1
  fi

  # Check if worktree already exists
  if [[ -d "$worktree_path" ]]; then
    echo -e "${YELLOW}Worktree already exists at: $worktree_path${NC}"
    echo -e "Switch to it instead? (y/n)"
    # No stdin (agent/CI): read fails, set -e would abort. Empty answer = decline.
    read -r response || response=""
    if [[ "$response" == "y" ]]; then
      switch_worktree "$branch_name"
    fi
    return
  fi

  echo -e "${BLUE}Creating worktree: $branch_name${NC}"
  echo "  From: $from_branch"
  echo "  Path: $worktree_path"

  # Fetch a fresh remote base without touching the caller's checkout.
  echo -e "${BLUE}Fetching $from_branch from origin...${NC}"
  local base_ref="origin/$from_branch"
  # GIT_TERMINAL_PROMPT=0: fail fast instead of hanging on a credential
  # prompt blocking on an inherited tty. A non-zero exit (offline, no
  # remote) falls back to the local branch ref below.
  if ! GIT_TERMINAL_PROMPT=0 git fetch --no-tags origin "$from_branch"; then
    echo -e "${YELLOW}Fetch failed; branching from local $from_branch instead${NC}"
    base_ref="$from_branch"
  fi

  # Create worktree
  mkdir -p "$WORKTREE_DIR"
  ensure_gitignore
  printf '%s\n' "$GIT_ROOT" > "$COMMON_DIR/whetstone-main-root"

  echo -e "${BLUE}Creating worktree...${NC}"
  git worktree add -b "$branch_name" "$worktree_path" "$base_ref"

  if [[ -n "${WORKTREE_SESSION_ID:-}" ]]; then
    printf '%s\n' "$WORKTREE_SESSION_ID" > "$(git -C "$worktree_path" rev-parse --git-path whetstone-owner)"
  else
    echo "Set WORKTREE_SESSION_ID before create to enable session-owned cleanup." >&2
  fi

  # Copy environment files
  copy_env_files "$worktree_path"

  echo -e "${GREEN}✓ Worktree created successfully!${NC}"
  echo ""
  echo "Run commands with this worktree as their workdir:"
  printf 'env -C %q <command>\n' "$worktree_path"
  echo ""
}

# List all worktrees
list_worktrees() {
  git worktree list
}

# Switch to a worktree
switch_worktree() {
  local worktree_name="$1"

  if [[ -z "$worktree_name" ]]; then
    list_worktrees >&2
    echo "Return the path of which worktree? (enter name)" >&2
    read -r worktree_name || worktree_name=""
  fi

  resolve_worktree "$worktree_name" || {
    echo "Error: registered worktree not found: $worktree_name" >&2
    return 1
  }
}

# Copy env files to an existing worktree (or current directory if in a worktree)
copy_env_to_worktree() {
  local worktree_name="$1"
  local worktree_path

  if [[ -z "$worktree_name" ]]; then
    # Check if we're currently in a worktree
    local current_dir="$CURRENT_ROOT"
    if [[ "$current_dir" == "$WORKTREE_DIR"/* ]]; then
      worktree_path="$current_dir"
      worktree_name=$(basename "$worktree_path")
      echo -e "${BLUE}Detected current worktree: $worktree_name${NC}"
    else
      echo -e "${YELLOW}Usage: worktree-manager.sh copy-env [worktree-name]${NC}"
      echo "Or run from within a worktree to copy to current directory"
      list_worktrees
      return 1
    fi
  else
    if ! worktree_path=$(resolve_worktree "$worktree_name"); then
      echo -e "${RED}Error: Worktree not found: $worktree_name${NC}"
      list_worktrees
      return 1
    fi
  fi

  copy_env_files "$worktree_path"
  echo ""
}

# Clean up completed worktrees
cleanup_worktrees() {
  if [[ $# -eq 0 || -z "${WORKTREE_SESSION_ID:-}" ]]; then
    echo "Usage: set WORKTREE_SESSION_ID before create; cleanup <owned-name> [owned-name...]" >&2
    return 1
  fi
  local name worktree_path owner_file status response
  local to_remove=()
  for name in "$@"; do
    worktree_path=$(resolve_worktree "$name") || return 1
    owner_file=$(git -C "$worktree_path" rev-parse --git-path whetstone-owner)
    if [[ "$CURRENT_ROOT" == "$worktree_path" || ! -f "$owner_file" || "$(cat "$owner_file")" != "$WORKTREE_SESSION_ID" ]]; then
      echo "Refusing current or unowned worktree: $worktree_path" >&2
      return 1
    fi
    status=$(git -C "$worktree_path" status --porcelain --untracked-files=all --ignored=matching) || return 1
    if [[ -n "$status" ]]; then
      echo "Refusing worktree with tracked, untracked, or ignored changes: $worktree_path" >&2
      return 1
    fi
    to_remove+=("$worktree_path")
  done
  printf 'Remove these session-owned clean worktrees?\n'
  printf '  %s\n' "${to_remove[@]}"
  echo "Confirm no process is using them. Remove? (y/n)"
  read -r response || response=""
  [[ "$response" == y ]] || return 0
  for worktree_path in "${to_remove[@]}"; do
    git worktree remove "$worktree_path" || return 1
    printf 'Removed: %s\n' "$worktree_path"
  done
}

# Main command handler
main() {
  local command="${1:-list}"

  case "$command" in
    create)
      create_worktree "${2:-}" "${3:-main}"
      ;;
    list|ls)
      list_worktrees
      ;;
    switch|go)
      switch_worktree "${2:-}"
      ;;
    copy-env|env)
      copy_env_to_worktree "${2:-}"
      ;;
    cleanup|clean)
      shift
      cleanup_worktrees "$@"
      ;;
    help)
      show_help
      ;;
    *)
      echo -e "${RED}Unknown command: $command${NC}"
      echo ""
      show_help
      exit 1
      ;;
  esac
}

show_help() {
  cat << EOF
Git Worktree Manager

Usage: worktree-manager.sh <command> [options]

Commands:
  create <branch-name> [from-branch]  Create new worktree (copies .env files automatically)
                                      (from-branch defaults to main)
  list | ls                           List all worktrees
  switch | go [name]                  Print registered worktree path for caller workdir
  copy-env | env [name]               Copy .env files from main repo to worktree
                                      (if name omitted, uses current worktree)
  cleanup | clean <name> [...]        Remove named clean worktrees owned by WORKTREE_SESSION_ID
  help                                Show this help message

Environment Files:
  - Automatically copies .env, .env.local, .env.test, etc. on create
  - Skips .env.example (should be in git)
  - Creates .backup files if destination already exists
  - Use 'copy-env' to refresh env files after main repo changes

Examples:
  worktree-manager.sh create feature-login
  worktree-manager.sh create feature-auth develop
  worktree-manager.sh switch feature-login
  worktree-manager.sh copy-env feature-login
  worktree-manager.sh copy-env                   # copies to current worktree
  worktree-manager.sh cleanup feature-login
  worktree-manager.sh list

EOF
}

# Run
main "$@"
