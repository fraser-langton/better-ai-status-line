#!/bin/bash
# Compatibility entry point. Installers invoke Python directly to avoid extra processes.
set -euo pipefail
here="${BASH_SOURCE[0]%/*}"
exec python3 "$here/statusline.py" "$@"
