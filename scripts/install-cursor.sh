#!/bin/bash
# Install for the Cursor CLI agent (not the IDE chat panel).
set -euo pipefail
here="${BASH_SOURCE[0]%/*}"
exec python3 "$here/install.py" --harness cursor "$@"
