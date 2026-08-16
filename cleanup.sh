#!/usr/bin/env bash
# Remove regenerable junk (bytecode, tool caches, temp files).
# Does not delete .pixi, .git, lockfiles, or fixtures.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if command -v pixi >/dev/null 2>&1 && [[ -d "$ROOT/.pixi" ]]; then
  exec pixi run python scripts/cleanup.py "$@"
fi
exec python3 scripts/cleanup.py "$@"
