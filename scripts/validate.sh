#!/bin/bash
# Smoke tests for scripts/statusline.sh (Claude Code + Cursor CLI payloads).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$here/statusline.sh"
strip_ansi() { perl -pe 's/\e\[[0-9;]*m//g'; }

CLAUDE_CONFIG_DIR=$(mktemp -d)
export CLAUDE_CONFIG_DIR BETTER_STATUSLINE_CAVEMAN=0

run() {
  local payload=$1
  printf '%s' "$payload" | bash "$script" | strip_ansi
}

assert_contains() {
  local name=$1 haystack=$2 needle=$3
  if ! printf '%s' "$haystack" | grep -Fq "$needle"; then
    echo "FAIL: $name — expected substring: $needle" >&2
    echo "  got: $haystack" >&2
    exit 1
  fi
}

assert_not_contains() {
  local name=$1 haystack=$2 needle=$3
  if printf '%s' "$haystack" | grep -Fq "$needle"; then
    echo "FAIL: $name — should not contain: $needle" >&2
    echo "  got: $haystack" >&2
    exit 1
  fi
}

# Cursor: session fields must win over last-call current_usage (was 145% / 291k).
cursor_payload='{"model":{"display_name":"Composer 2.5"},"session_id":"abc","context_window":{"context_window_size":200000,"used_percentage":72.5,"total_input_tokens":145000,"current_usage":{"input_tokens":291000}}}'
out=$(run "$cursor_payload")
line1=$(printf '%s\n' "$out" | head -1)
assert_contains "cursor ctx pct" "$line1" "Ctx: 72%"
assert_contains "cursor token pair" "$line1" "(145k/200k)"
assert_not_contains "cursor bogus pct" "$line1" "Ctx: 145%"

# Claude Code: live prompt from current_usage when session totals are absent.
claude_payload='{"model":{"display_name":"Opus 4.6"},"context_window":{"context_window_size":1000000,"current_usage":{"input_tokens":165000,"cache_read_input_tokens":10000}}}'
out=$(run "$claude_payload")
line1=$(printf '%s\n' "$out" | head -1)
assert_contains "claude ctx pct" "$line1" "Ctx: 17%"
assert_contains "claude token pair" "$line1" "175k/1M"

# Cursor: param_summary when effort.level is absent.
cursor_effort_payload='{"version":"1.0","model":{"id":"grok-4.5","display_name":"Grok 4.5","param_summary":"High"}}'
out=$(run "$cursor_effort_payload")
line1=$(printf '%s\n' "$out" | head -1)
assert_contains "cursor param_summary effort" "$line1" "Effort: High"
assert_not_contains "cursor effort auto" "$line1" "Effort: auto"

echo "OK: statusline.sh validation passed"
