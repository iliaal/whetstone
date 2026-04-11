#!/usr/bin/env bash
set -Eeuo pipefail

# Update the locally installed compound-engineering plugin to the latest
# pushed version by driving the modern Claude Code CLI commands.
#
# This script used to hand-roll the update (pull marketplace clone, copy
# plugin files into versioned cache, patch installed_plugins.json, orphan
# old cached versions, touch known_marketplaces.json timestamp). That was
# a workaround for a past Claude Code bug where the marketplace clone was
# never git-pulled, so new versions sat orphaned in cache and the CLI
# thought the installed copy was already latest.
#
# Modern Claude Code exposes `claude plugin marketplace update` (refreshes
# the marketplace clone) and `claude plugin update` (bumps the installed
# version from the refreshed clone). This wrapper just drives those two
# commands in the right order and echoes status.
#
# Usage: bash scripts/update-plugin.sh
#
# Safe to run repeatedly — idempotent. Both CLI commands are no-ops if
# nothing changed upstream.

MARKETPLACE_NAME="iliaal-marketplace"
PLUGIN_KEY="compound-engineering@${MARKETPLACE_NAME}"

echo "Refreshing marketplace clone: $MARKETPLACE_NAME"
claude plugin marketplace update "$MARKETPLACE_NAME"

echo ""
echo "Updating installed plugin: $PLUGIN_KEY"
claude plugin update "$PLUGIN_KEY"

echo ""
echo "Done. Restart Claude Code to pick up the new version."
