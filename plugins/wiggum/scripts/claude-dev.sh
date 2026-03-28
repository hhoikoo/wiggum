#!/usr/bin/env bash
set -euo pipefail

# Launch claude with local wiggum plugin for development testing.
# Usage: ./bin/claude-dev [claude args...]

REPO_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/../../.." && pwd)"

exec claude \
  --plugin-dir "$REPO_DIR/plugins/wiggum" \
  --settings '{"enabledPlugins":{"wiggum@wiggum":false}}' \
  "$@"
