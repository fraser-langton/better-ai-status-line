---
description: Install the better-ai-status-line status line into your Claude Code settings
argument-hint: "[--force]"
allowed-tools: Bash
---

Install the better-ai-status-line status line by running:

```
bash "${CLAUDE_PLUGIN_ROOT}/scripts/install.sh" $ARGUMENTS
```

- On success, tell the user the status line is installed and appears on their next prompt.
- If it exits with code 2, a different status line is already configured. Show the user the existing command it printed and ask whether to replace it. Only if they say yes, re-run with `--force`.
- If it fails because `jq` is missing, tell the user how to install it.

Then mention that Codex users can get a matching status line by pasting the block printed by `bash "${CLAUDE_PLUGIN_ROOT}/scripts/install.sh" --codex` into `~/.codex/config.toml`.
