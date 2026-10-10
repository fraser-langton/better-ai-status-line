# better-ai-status-line

A cost-aware status line for [Claude Code](https://claude.com/claude-code), plus a matching config for OpenAI's Codex CLI. You see what a session is costing you without having to run `/cost` or `/usage`.

```
Model: Opus 5.5 | Effort: high | 5h: 42% (1h30m) | 7d: 81% (2d7h) | Cost: $1.23 | Ctx: 16% (165k/1M, compact @600k)
```

Each segment changes colour as it gets expensive: green, then yellow, then red.

| Segment | Shows | Colour |
| --- | --- | --- |
| Model | current model | Haiku green, Sonnet yellow, Opus/Fable red |
| Effort | reasoning effort | low green → max red |
| 5h / 7d | subscription rate-limit usage and time until reset | ≥50% yellow, ≥80% red |
| Cost | session cost in USD | ≥$1 yellow, ≥$5 red |
| Ctx | context used, tokens/window, and the auto-compact point if set | ≥50% yellow, ≥80% red |

Rate-limit segments only appear when Claude Code reports them, which happens on Pro/Max subscriptions. If the [caveman](https://github.com/JuliusBrussee/caveman) plugin is installed, its badge goes on the end.

## Install (Claude Code)

Requires `bash`, `jq` and `awk`.

Type this at the prompt in a Claude Code session:

```
/plugin install better-ai-status-line --marketplace fraser-langton/better-ai-status-line
```

Answer `y` to add the marketplace, then pick a scope. Then run:

```
/better-ai-status-line:setup
```

Setup copies the script to `~/.claude/better-ai-status-line/statusline.sh` and sets `statusLine` in `~/.claude/settings.json`, backing that file up first. If you already have a status line, it asks before replacing it. After a plugin update, run setup again to get the new script.

### Manual install

```sh
git clone https://github.com/fraser-langton/better-ai-status-line
bash better-ai-status-line/scripts/install.sh            # add --force to replace an existing status line
```

## Install (Codex)

Codex builds its status line from built-in items, so you only need config. Paste [`codex/config.toml`](codex/config.toml) into `~/.codex/config.toml`. If you already have a `[tui]` table, merge the keys into it instead.

```toml
[tui]
status_line_use_colors = true
status_line = [
    "model-with-reasoning",
    "five-hour-limit",
    "weekly-limit",
    "estimated-thread-cost",
    "context-used",
    "context-window-size",
]
```

## Options

Set these as environment variables, for example in the `env` block of `~/.claude/settings.json`:

| Variable | Effect |
| --- | --- |
| `BETTER_STATUSLINE_CTX_BUDGET` | Measure context against this many tokens instead of the model's full window. For example, `700000` matches a Codex `model_context_window = 700000`. Display only. |
| `BETTER_STATUSLINE_CAVEMAN` | Path to `caveman-statusline.sh`, or `0` to hide the badge. Auto-detected when unset. |

## Uninstall

Remove `statusLine` from `~/.claude/settings.json` (or restore the `settings.json.bak-*` backup), delete `~/.claude/better-ai-status-line/`, then run `/plugin uninstall better-ai-status-line`.

## License

MIT
