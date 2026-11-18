#!/bin/bash
# Install for Claude Code. --codex prints the matching native Codex configuration.
set -euo pipefail
here="${BASH_SOURCE[0]%/*}"
exec python3 "$here/install.py" --harness claude "$@"
