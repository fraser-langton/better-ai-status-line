#!/bin/bash
# Install better-ai-status-line as Claude Code's status line.
#
# Copies statusline.sh to a stable path under the Claude config dir (plugin
# folders change on every update) and points settings.json's statusLine at it.
# Re-run after updating the plugin to pick up a new version of the script.
#
# Usage: install.sh [--force] [--codex]
#   --force  replace an existing, different statusLine setting
#   --codex  print the Codex [tui] block to paste into ~/.codex/config.toml
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
settings="$config_dir/settings.json"
target_dir="$config_dir/better-ai-status-line"
target="$target_dir/statusline.sh"
command="bash \"$target\""

force=0
codex=0
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    --codex) codex=1 ;;
    *) echo "unknown option: $arg" >&2; exit 64 ;;
  esac
done

if [ "$codex" = 1 ]; then
  cat "$here/../codex/config.toml"
  exit 0
fi

command -v jq >/dev/null || { echo "better-ai-status-line needs jq: brew install jq (or your package manager)" >&2; exit 1; }

[ -f "$settings" ] || { mkdir -p "$config_dir"; echo '{}' > "$settings"; }

current=$(jq -r '.statusLine.command // empty' "$settings")

# ai-state-machine wraps the status line and runs the command saved in its
# wrapped-statusline file. Install there instead of replacing its wrapper.
asm_home="${ASM_HOME:-$HOME/.ai-state-machine}"
if [[ "$current" == *"$asm_home/bin/asm"*statusline* ]]; then
  mkdir -p "$target_dir"
  cp "$here/statusline.sh" "$target"
  chmod +x "$target"
  printf '%s\n' "$command" > "$asm_home/wrapped-statusline"
  echo "Installed status line script: $target"
  echo "ai-state-machine wraps the status line; set it to run this one: $asm_home/wrapped-statusline"
  exit 0
fi

if [ -n "$current" ] && [ "$current" != "$command" ] && [ "$force" != 1 ]; then
  echo "settings.json already has a status line:" >&2
  echo "  $current" >&2
  echo "Re-run with --force to replace it (settings.json is backed up first)." >&2
  exit 2
fi

mkdir -p "$target_dir"
cp "$here/statusline.sh" "$target"
chmod +x "$target"
echo "Installed status line script: $target"

if [ "$current" = "$command" ]; then
  echo "settings.json already points at it; left unchanged."
  exit 0
fi

backup="$settings.bak-$(date +%Y%m%d-%H%M%S)"
cp "$settings" "$backup"
tmp=$(mktemp)
jq --arg cmd "$command" '.statusLine = {type: "command", command: $cmd, padding: 2}' "$settings" > "$tmp"
mv "$tmp" "$settings"

echo "Updated: $settings (backup: $backup)"
