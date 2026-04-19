#!/usr/bin/env bash
# Launch Edge with the compound-engineering profile via the unified edge-cdp framework.
# Profile registry: ~/.config/edge-cdp/profiles.toml
# Source: ~/ai/edge-cdp
set -euo pipefail
exec edge-cdp ensure compound-engineering
