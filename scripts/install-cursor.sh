#!/bin/bash
# Install better-ai-status-line for the Cursor CLI agent.
#
# Copies statusline.sh to ~/.cursor/better-ai-status-line/ and sets statusLine
# in ~/.cursor/cli-config.json. The IDE chat panel does not use this hook.
#
# Usage: install-cursor.sh [--force]
#   --force  replace an existing, different statusLine setting
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_dir="$HOME/.cursor"
settings="$config_dir/cli-config.json"
target_dir="$config_dir/better-ai-status-line"
target="$target_dir/statusline.sh"
command="bash \"$target\""

force=0
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    *) echo "unknown option: $arg" >&2; exit 64 ;;
  esac
done

command -v jq >/dev/null || { echo "better-ai-status-line needs jq: brew install jq (or your package manager)" >&2; exit 1; }

[ -f "$settings" ] || { mkdir -p "$config_dir"; echo '{"permissions":{"allow":[],"deny":[]},"version":1}' > "$settings"; }

current=$(jq -r '.statusLine.command // empty' "$settings")
if [ -n "$current" ] && [ "$current" != "$command" ] && [ "$force" != 1 ]; then
  echo "cli-config.json already has a status line:" >&2
  echo "  $current" >&2
  echo "Re-run with --force to replace it (cli-config.json is backed up first)." >&2
  exit 2
fi

mkdir -p "$target_dir"
cp "$here/statusline.sh" "$target"
chmod +x "$target"
echo "Installed status line script: $target"

if [ "$current" = "$command" ]; then
  echo "cli-config.json already points at it; left unchanged."
  exit 0
fi

backup="$settings.bak-$(date +%Y%m%d-%H%M%S)"
cp "$settings" "$backup"
tmp=$(mktemp)
jq --arg cmd "$command" '.statusLine = {type: "command", command: $cmd, padding: 2}' "$settings" > "$tmp"
mv "$tmp" "$settings"

echo "Updated: $settings (backup: $backup)"
echo "Restart or start a new Cursor CLI agent session to load the status line."
