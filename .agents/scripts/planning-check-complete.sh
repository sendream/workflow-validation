#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ROOT=${1:-$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)}

python3 "$SCRIPT_DIR/planning-hook.py" check-complete "$ROOT"
