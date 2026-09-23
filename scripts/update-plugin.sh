#!/usr/bin/env bash
set -Eeuo pipefail

# Update the locally installed whetstone plugin to the latest pushed version:
# `claude plugin marketplace update` refreshes the marketplace clone, then
# `claude plugin update` installs from it. Idempotent.
#
# Usage: bash scripts/update-plugin.sh

MARKETPLACE_NAME="iliaal-marketplace"
PLUGIN_KEY="whetstone@${MARKETPLACE_NAME}"

echo "Refreshing marketplace clone: $MARKETPLACE_NAME"
claude plugin marketplace update "$MARKETPLACE_NAME"

echo ""
echo "Updating installed plugin: $PLUGIN_KEY"
claude plugin update "$PLUGIN_KEY"

echo ""
echo "Done. Restart Claude Code to pick up the new version."
