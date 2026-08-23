#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  capture-run-script.sh --run-id <run-id> --script <path> [--command <command>] [--output <path>]

Copies a temporary verification script into .agent-state/runs/<run-id>/scripts/
and writes a small JSON metadata file with sha256, command, source path, and output artifact.
EOF
}

ROOT=$(CDPATH= cd "$(dirname "$0")/../.." && pwd)
RUN_ID=""
SCRIPT_PATH=""
COMMAND_TEXT=""
OUTPUT_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-id)
      RUN_ID=${2:-}
      shift 2
      ;;
    --script)
      SCRIPT_PATH=${2:-}
      shift 2
      ;;
    --command)
      COMMAND_TEXT=${2:-}
      shift 2
      ;;
    --output)
      OUTPUT_PATH=${2:-}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'capture-run-script: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$RUN_ID" ] || [ -z "$SCRIPT_PATH" ]; then
  usage >&2
  exit 2
fi

case "$RUN_ID" in
  *[!A-Za-z0-9._-]*|"")
    printf 'capture-run-script: unsafe run id: %s\n' "$RUN_ID" >&2
    exit 2
    ;;
esac

if [ ! -f "$SCRIPT_PATH" ]; then
  printf 'capture-run-script: script not found: %s\n' "$SCRIPT_PATH" >&2
  exit 2
fi

SCRIPT_DIR="$ROOT/.agent-state/runs/$RUN_ID/scripts"
mkdir -p "$SCRIPT_DIR"

BASE=$(basename "$SCRIPT_PATH")
DEST="$SCRIPT_DIR/$BASE"
cp "$SCRIPT_PATH" "$DEST"

if command -v sha256sum >/dev/null 2>&1; then
  SHA=$(sha256sum "$DEST" | awk '{print $1}')
else
  SHA=$(shasum -a 256 "$DEST" | awk '{print $1}')
fi

META="$DEST.capture.json"
python3 - "$SCRIPT_PATH" "$DEST" "$SHA" "$COMMAND_TEXT" "$OUTPUT_PATH" > "$META" <<'PY'
import json
import sys

source, captured, sha, command, output = sys.argv[1:]
json.dump(
    {
        "source": source,
        "captured": captured,
        "sha256": sha,
        "command": command or None,
        "output_artifact": output or None,
    },
    sys.stdout,
    ensure_ascii=False,
    indent=2,
)
sys.stdout.write("\n")
PY

printf 'captured script: %s\n' "$DEST"
printf 'metadata: %s\n' "$META"
