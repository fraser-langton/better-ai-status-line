#!/bin/bash
# better-ai-status-line — status line for Claude Code and the Cursor CLI agent:
# model, effort, rate limits, cost and context, with an optional caveman badge.
# Colors scale with cost: cheap/low stays green, expensive/high goes red.
#
# Reads status-line JSON on stdin (Claude Code or Cursor CLI). Needs bash, jq and awk.
#
# Optional environment:
#   BETTER_STATUSLINE_CAVEMAN     path to caveman-statusline.sh; auto-detected
#                                 when unset. Set to 0 to hide the badge.

input=$(cat)
config_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

model=$(printf '%s' "$input" | jq -r '.model.display_name // "?"')
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
effort=$(printf '%s' "$input" | jq -r '.effort.level // "auto"')
five_hour=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty | floor')
five_resets=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // 0')
seven_day=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty | floor')
seven_resets=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.resets_at // 0')
cost=$(printf '%s' "$input" | jq -r '.cost.total_cost_usd // 0 | (.*100|round)/100')

# Context: session fill vs window. Claude Code uses current_usage for the live
# prompt; Cursor CLI uses used_percentage + total_input_tokens (current_usage
# is last-call only and can exceed context_window_size).
ctx_window=$(printf '%s' "$input" | jq -r '.context_window.context_window_size // empty')
ctx_used_pct=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')
ctx_total_input=$(printf '%s' "$input" | jq -r '.context_window.total_input_tokens // empty')
ctx_call_tokens=$(printf '%s' "$input" | jq -r '.context_window.current_usage // empty
  | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0)')
ctx_compact=$(jq -r '.autoCompactWindow // empty' "$config_dir/settings.json" 2>/dev/null)
ctx_display_tokens=""
if [ -n "$ctx_total_input" ] && [ "$ctx_total_input" != "null" ]; then
  ctx_display_tokens=$ctx_total_input
elif [ -n "$ctx_call_tokens" ]; then
  ctx_display_tokens=$ctx_call_tokens
fi
ctx=""
if [ -n "$ctx_used_pct" ] && [ "$ctx_used_pct" != "null" ]; then
  ctx=$(printf '%s' "$ctx_used_pct" | awk '{printf "%d", $1}')
elif [ -n "$ctx_display_tokens" ] && [ -n "$ctx_window" ] && [ "$ctx_window" -gt 0 ]; then
  ctx=$((ctx_display_tokens * 100 / ctx_window))
fi

# 165486 -> 165k, 1000000 -> 1M
fmt_tokens() {
  awk -v n="$1" 'BEGIN {
    if (n >= 1000000) { s = sprintf("%.1f", n / 1000000); sub(/\.0$/, "", s); print s "M" }
    else if (n >= 1000) printf "%dk\n", n / 1000
    else print n
  }'
}

# --- color helpers (256-color ANSI) ---
color() { printf '\033[38;5;%sm%s\033[0m' "$1" "$2"; }
color_bold() { printf '\033[1;38;5;%sm%s\033[0m' "$1" "$2"; }

model_color() {
  case "$1" in
    *Haiku*) echo 82 ;;   # green — cheap
    *Sonnet*) echo 220 ;; # yellow — mid
    *Fable*) echo 196 ;;  # red — expensive
    *Opus*) echo 196 ;;   # red — expensive
    *) echo 244 ;;        # grey — unknown
  esac
}

effort_color() {
  case "$1" in
    low) echo 82 ;;
    medium) echo 37 ;;
    high) echo 220 ;;
    xhigh) echo 208 ;;
    max) echo 196 ;;
    *) echo 244 ;;        # auto / unrecognized
  esac
}

pct_color() {
  n=$1
  if [ "$n" -ge 80 ]; then echo 196
  elif [ "$n" -ge 50 ]; then echo 220
  else echo 82
  fi
}

cost_color() {
  awk -v c="$1" 'BEGIN { if (c >= 5) print 196; else if (c >= 1) print 220; else print 82 }'
}

format_reset() {
  local resets_at=$1
  if [ -z "$resets_at" ] || [ "$resets_at" -eq 0 ]; then
    echo ""
    return
  fi
  local now=$(date +%s)
  local secs=$((resets_at - now))
  if [ "$secs" -le 0 ]; then
    echo "now"
  elif [ "$secs" -lt 60 ]; then
    echo "${secs}s"
  elif [ "$secs" -lt 3600 ]; then
    local mins=$((secs / 60))
    echo "${mins}m"
  elif [ "$secs" -lt 86400 ]; then
    local hours=$((secs / 3600))
    local mins=$(((secs % 3600) / 60))
    echo "${hours}h${mins}m"
  else
    local days=$((secs / 86400))
    local hours=$(((secs % 86400) / 3600))
    echo "${days}d${hours}h"
  fi
}

# Print " | <label>: <pct>% (<reset>)" for a rate-limit window, if it has a reading.
limit_segment() {
  local label=$1 pct=$2 resets_at=$3
  [ -z "$pct" ] && return
  printf ' | %s: ' "$label"
  color "$(pct_color "$pct")" "${pct}%"
  local reset
  reset=$(format_reset "$resets_at")
  [ -n "$reset" ] && printf ' (%s)' "$reset"
}

# The caveman plugin's badge script, if installed.
find_caveman() {
  if [ -n "${BETTER_STATUSLINE_CAVEMAN:-}" ]; then
    [ "$BETTER_STATUSLINE_CAVEMAN" != "0" ] && echo "$BETTER_STATUSLINE_CAVEMAN"
    return
  fi
  local candidate
  for candidate in \
    "$config_dir/hooks/caveman-statusline.sh" \
    "$config_dir/plugins/marketplaces/caveman/hooks/caveman-statusline.sh"; do
    [ -f "$candidate" ] && { echo "$candidate"; return; }
  done
}

MODEL_C=$(model_color "$model")

printf 'Model: '
if [[ "$model" == *Fable* ]]; then
  color_bold "$MODEL_C" "$model"
else
  color "$MODEL_C" "$model"
fi
printf ' | Effort: '
color "$(effort_color "$effort")" "$effort"
limit_segment 5h "$five_hour" "$five_resets"
limit_segment 7d "$seven_day" "$seven_resets"
printf ' | Cost: '
color "$(cost_color "$cost")" "\$$cost"
if [ -n "$ctx" ]; then
  printf ' | Ctx: '
  color "$(pct_color "$ctx")" "${ctx}%"
  if [ -n "$ctx_display_tokens" ] && [ -n "$ctx_window" ]; then
    printf ' (%s/%s' "$(fmt_tokens "$ctx_display_tokens")" "$(fmt_tokens "$ctx_window")"
    [ -n "$ctx_compact" ] && [ "$ctx_compact" -lt "$ctx_window" ] && printf ', compact @%s' "$(fmt_tokens "$ctx_compact")"
    printf ')'
  fi
fi

caveman_script=$(find_caveman)
if [ -n "$caveman_script" ] && [ -f "$caveman_script" ]; then
  caveman=$(bash "$caveman_script" 2>/dev/null)
  [ -n "$caveman" ] && printf ' %s' "$caveman"
fi

# Second line: IDs for resuming and finding this session, in the slate grey
# Codex uses for its thread ID.
ID_C=103
ids=()
[ -n "$session_id" ] && ids+=("Session: $(color "$ID_C" "$session_id")")
# Superset (superset.sh) agent tabs export these; shown only when present.
[ -n "${SUPERSET_WORKSPACE_ID:-}" ] && ids+=("Superset ws: $(color "$ID_C" "$SUPERSET_WORKSPACE_ID")")
[ -n "${SUPERSET_TERMINAL_ID:-}" ] && ids+=("term: $(color "$ID_C" "$SUPERSET_TERMINAL_ID")")
if [ "${#ids[@]}" -gt 0 ]; then
  printf '\n%s' "${ids[0]}"
  for id in "${ids[@]:1}"; do printf ' | %s' "$id"; done
fi
