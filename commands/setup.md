---
description: Install the better-ai-status-line status line into your Claude Code settings
argument-hint: "[--force]"
allowed-tools: Bash
---

Install the persistent shared renderer by running:

```sh
bash "${CLAUDE_PLUGIN_ROOT}/scripts/install.sh" $ARGUMENTS
```

- On success, report the changed settings and backup paths; restart Claude Code to load the status line.
- Exit code 2 means a different status line is configured. Show the existing command and ask before replacing it unless replacement is already authorised. Use `--force` only with that authorisation.
- Python 3.9+ is required. If missing, explain how to install Python using the platform's package manager.
- Existing installs of this package and ai-state-machine wrappers can be upgraded directly. Workflow progress still reads ASM's cache; its hooks and history remain unchanged.

For other requested CLIs, the repository provides `scripts/install-cursor.sh`, `scripts/install-antigravity.sh`, and the native Codex block printed by `scripts/install.sh --codex`. Do not configure paths under the temporary plugin clone.
