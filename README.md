**To install, paste this into your AI coding agent:**

```text
Install the better-ai-status-line status line from https://github.com/fraser-langton/better-ai-status-line into the AI coding tool you are running in.

1. Clone the repo into a temporary directory and read README.md.
2. For Claude Code, run bash <clone>/scripts/install.sh. For Cursor CLI, run bash <clone>/scripts/install-cursor.sh. For Antigravity CLI, run bash <clone>/scripts/install-antigravity.sh. These require Python 3.9+ and install the renderer at a persistent path outside the clone. Do not configure a command under /tmp.
3. If the installer exits with code 2, show the existing command. Use --force only if replacing it is already authorised or the user agrees. Installers back up changed settings and preserve unrelated keys.
4. For Codex, back up ~/.codex/config.toml and merge only status_line and status_line_use_colors from codex/config.toml into its existing [tui] table. Keep other settings.
5. Only install other CLIs if requested. For another tool, check its supported footer interface before changing settings.
6. Report the changed paths, backup locations, and restart requirement.
```

# better-ai-status-line

A shared, cost-aware status line for Claude Code, Cursor CLI and Antigravity CLI, plus the closest matching native footer configuration for Codex.

```text
Model: Opus 5.5 | Effort: high | 5h: 42% (1h30m) | 7d: 81% (2d7h) | Cost: $1.23 | Ctx: 16% (165k/1M, compact @600k) [CAVEMAN]
Session: 7f3c2a10-… | Superset ws: 4b9e0c22-… | term: a17d5f3e-…
```

The three command-based CLIs share labels, field order and colours. Each shows only the metrics it supplies; an absent cost or limit is hidden, while an actual zero is displayed. IDs go on a second line.

| Segment | Shows | Colour |
| --- | --- | --- |
| Model | Current model | Haiku/Flash green, Sonnet/Pro yellow, Opus/Fable/Ultra red |
| Effort | Reasoning effort | Low green → max red |
| 5h / 7d | Rate-limit usage and time until reset | ≥50% yellow, ≥80% red |
| Quota | Antigravity quota used and time until reset | ≥50% yellow, ≥80% red |
| Cost | Reported session cost in USD | ≥$1 yellow, ≥$5 red |
| Ctx | Context used and tokens/window | ≥50% yellow, ≥80% red |
| Session | Session or conversation ID | Slate grey |
| Superset | Workspace and terminal IDs when exported by Superset/Paradev | Slate grey |

Subscription limits and cost depend on the host and account. Cursor does not currently supply all of Claude's metrics. Antigravity's model label supplies effort when no separate effort field exists.

## Install

Requires Python 3.9+ and Bash for the installer entry points. The renderer uses only the Python standard library; `jq` and `awk` are no longer required.

```sh
git clone https://github.com/fraser-langton/better-ai-status-line
cd better-ai-status-line
```

Choose the relevant installer:

| CLI | Command | Settings | Installed renderer |
| --- | --- | --- | --- |
| Claude Code | `bash scripts/install.sh` | `~/.claude/settings.json` | `~/.claude/better-ai-status-line/statusline.py` |
| Cursor CLI | `bash scripts/install-cursor.sh` | `~/.cursor/cli-config.json` | `~/.cursor/better-ai-status-line/statusline.py` |
| Antigravity CLI | `bash scripts/install-antigravity.sh` | `~/.gemini/antigravity-cli/settings.json` | `~/.gemini/antigravity-cli/better-ai-status-line/statusline.py` |

Installers copy the renderer out of the clone and configure the current Python interpreter using an absolute path. The temporary clone can then be deleted. Restart the affected CLI to load the settings. Cursor IDE chat does not use this hook.

An unrelated status line is left alone (exit code 2). Add `--force` to replace it. Existing installs of this package can be upgraded by rerunning the installer. Changes preserve unrelated settings and status-line options, with a timestamped backup beside the settings file. Cursor gets a minimum five-second timeout and a one-second update interval to tolerate busy machines.

Config-directory overrides are supported: `CLAUDE_CONFIG_DIR`, `CURSOR_CONFIG_DIR` / `CURSOR_CONFIG_PATH`, and `GEMINI_CONFIG_DIR`. On Cursor, set `CURSOR_CONFIG_PATH` to a full settings-file path. The renderer uses it when resolving model effort.

### Claude Code plugin

```text
/plugin install better-ai-status-line --marketplace fraser-langton/better-ai-status-line
/better-ai-status-line:setup
```

Add the marketplace and choose the desired scope when prompted. Rerun setup after plugin updates to refresh the persistent renderer.

### Codex

Codex's native footer controls its labels, colours, separators and layout. It cannot exactly reproduce the other three using this configuration. Back up `~/.codex/config.toml` and merge the keys in [`codex/config.toml`](codex/config.toml) into the existing `[tui]` table:

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
    "thread-id",
]
```

Limit items show **remaining** allowance in Codex; the command renderer shows **used** allowance. Estimated cost appears only where Codex reports it. `bash scripts/install.sh --codex` prints this block without changing files.

## Payload handling

Claude Code uses `context_window.current_usage` (input plus cache creation/read tokens) for the current prompt, rather than cumulative input tokens across the conversation. Its `autoCompactWindow` setting appears only on Claude's line.

Cursor uses `context_window.used_percentage` for session fill, with tokens/window derived from that percentage when available. Its last-call `current_usage` can exceed the session window and must not determine fill. Effort comes from `model.param_summary`, then the matching selected model's parameters in CLI config.

Antigravity supports `conversation_id`, effort in a model label such as `Gemini 4 Carbon (Medium)`, and quota `remaining_fraction` / `used_percentage` with reset times. Model-specific quota is selected by model ID; when no ID matches, a single quota entry is accepted, but multiple entries are not guessed. Floating-point rounding cannot turn 20% into 19%.

## Performance and workflow progress

The default renderer starts no child processes. It parses the input once and reads small local settings/cache files directly. The former shell renderer launched many `jq`, `awk` and badge subprocesses on each redraw, which could take several seconds under endpoint scanning or load and cause `signal: killed` / missing footer errors.

[`scripts/statusline.sh`](scripts/statusline.sh) remains a compatibility entry point. Installers invoke Python directly to avoid the extra shell process.

With [ai-state-machine](https://github.com/fraser-langton/ai-state-machine), the renderer reads the existing session cache and machine configuration to display the workflow progress line. Both `path` and `stages` styles are supported. Installers recognise ASM wrappers and replace the rendering command with this direct renderer, keeping ASM hooks, cached history and wrapped-command files intact. If ASM is installed again later and wraps this renderer, rerun this package's installer to restore direct rendering and avoid duplicate progress lines.

## Caveman badge

When [Caveman](https://github.com/JuliusBrussee/caveman) is installed, the default renderer reads its short mode and savings files directly. It refuses symlinked flag/suffix files and strips control characters.

| Environment variable | Effect |
| --- | --- |
| `BETTER_STATUSLINE_CAVEMAN=0` | Hide the badge |
| `BETTER_STATUSLINE_CAVEMAN=/path/to/script.sh` | Run an explicit custom badge script with a 250ms timeout; this optional override starts a child process |
| `CAVEMAN_STATUSLINE_SAVINGS=0` | Hide the cached savings suffix |
| `CLAUDE_CONFIG_DIR` | Locate Claude settings and Caveman files for any harness |
| `ASM_HOME` / `ASM_MACHINE` | Override the workflow cache directory / machine file |

## Verify changes

```sh
bash scripts/validate.sh
printf '%s' '{"model":{"display_name":"Gemini 4 Carbon (Medium)"},"quota":{"carbon":{"remaining_fraction":0.8}}}' | python3 scripts/statusline.py antigravity
```

The tests cover host payload interpretation, missing versus zero metrics, quota selection/rounding, badge safety, workflow cache rendering, persistent installs, upgrades, backups and settings preservation. They use temporary directories, not live CLI settings.

## Uninstall

Restore the backup beside the relevant settings file, or remove its `statusLine` entry, then delete that CLI's `better-ai-status-line` directory. For a Claude plugin installation, also run `/plugin uninstall better-ai-status-line`.

## License

MIT
