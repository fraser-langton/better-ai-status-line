#!/bin/bash
# Run renderer and installer regression tests without touching live settings.
set -euo pipefail
here="${BASH_SOURCE[0]%/*}"
exec python3 -m unittest discover -s "$here/../tests" -v
