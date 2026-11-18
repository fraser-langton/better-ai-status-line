#!/bin/bash
# Install for Antigravity CLI at a persistent path, never under /tmp.
set -euo pipefail
here="${BASH_SOURCE[0]%/*}"
exec python3 "$here/install.py" --harness antigravity "$@"
