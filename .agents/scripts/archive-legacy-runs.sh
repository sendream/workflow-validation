#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  archive-legacy-runs.sh --dry-run
  archive-legacy-runs.sh --manifest-only
  archive-legacy-runs.sh --archive

Maintains legacy .agents/runs evidence. This script never deletes evidence.
--dry-run prints a summary, --manifest-only writes a manifest, and --archive
moves legacy run entries into .agent-state/runs/_archive/<timestamp>/legacy-agents-runs/.
EOF
}

ROOT=$(CDPATH= cd "$(dirname "$0")/../.." && pwd)
MODE=""

if [ "$#" -eq 0 ]; then
  usage >&2
  exit 2
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--manifest-only|--archive)
      MODE=$1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'archive-legacy-runs: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

LEGACY="$ROOT/.agents/runs"
STATE_ARCHIVE="$ROOT/.agent-state/runs/_archive"

if [ ! -d "$LEGACY" ]; then
  printf 'legacy runs directory not found: %s\n' "$LEGACY"
  exit 0
fi

MANIFEST="$LEGACY/_legacy_manifest.json"
TMP_MANIFEST=$(mktemp "${TMPDIR:-/tmp}/codex-legacy-runs.XXXXXX")
trap 'rm -f "$TMP_MANIFEST"' EXIT INT TERM
python3 - "$LEGACY" > "$TMP_MANIFEST" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
entries = []
total_bytes = 0
for path in sorted(root.rglob("*")):
    if path.name in {".gitignore", "README.md", "_legacy_manifest.json"}:
        continue
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        continue
    if path.is_file():
        size = path.stat().st_size
        total_bytes += size
        entries.append({"path": rel, "type": "file", "bytes": size})
    elif path.is_dir():
        entries.append({"path": rel, "type": "dir"})

json.dump(
    {
        "legacy_root": str(root),
        "entry_count": len(entries),
        "total_file_bytes": total_bytes,
        "entries": entries[:500],
        "truncated": len(entries) > 500,
    },
    sys.stdout,
    ensure_ascii=False,
    indent=2,
)
sys.stdout.write("\n")
PY

COUNT=$(python3 - "$TMP_MANIFEST" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print(data["entry_count"])
PY
)
BYTES=$(python3 - "$TMP_MANIFEST" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print(data["total_file_bytes"])
PY
)

printf 'legacy runs entries: %s\n' "$COUNT"
printf 'legacy runs bytes: %s\n' "$BYTES"

case "$MODE" in
  --dry-run)
    printf 'dry-run only; no files changed\n'
    ;;
  --manifest-only)
    mv "$TMP_MANIFEST" "$MANIFEST"
    printf 'manifest written: %s\n' "$MANIFEST"
    ;;
  --archive)
    TS=$(date +%Y%m%d-%H%M%S)
    DEST="$STATE_ARCHIVE/$TS/legacy-agents-runs"
    mkdir -p "$DEST" "$STATE_ARCHIVE/$TS"
    mv "$TMP_MANIFEST" "$STATE_ARCHIVE/$TS/_legacy_manifest.json"
    find "$LEGACY" -mindepth 1 -maxdepth 1 \
      ! -name '.gitignore' \
      ! -name 'README.md' \
      ! -name '_legacy_manifest.json' \
      -exec mv {} "$DEST"/ \;
    printf 'archived legacy runs to: %s\n' "$DEST"
    printf 'manifest written: %s\n' "$STATE_ARCHIVE/$TS/_legacy_manifest.json"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
