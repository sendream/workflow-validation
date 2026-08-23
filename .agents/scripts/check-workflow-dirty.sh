#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)
. "$SCRIPT_DIR/portable.sh"
STATE_DIR="$ROOT/.agent-state/flags"
LEGACY_STATE_DIR="$ROOT/.agents/state"
LAST_FILE="$STATE_DIR/workflow-smoke.last"
LEGACY_LAST_FILE="$LEGACY_STATE_DIR/workflow-smoke.last"
DIRTY_FLAG="$STATE_DIR/workflow-dirty.flag"
LEGACY_DIRTY_FLAG="$LEGACY_STATE_DIR/workflow-dirty.flag"
FINGERPRINT_FILE="$STATE_DIR/workflow-assets.fingerprint"
STATE_COMPAT="$SCRIPT_DIR/state-compat.py"
STATE_COMPAT_DEPRECATED_SINCE="2026-07-22"
STATE_COMPAT_REMOVE_AFTER="2026-12-31"
MAX_WORKFLOW_ASSETS="${CODEX_WORKFLOW_FINGERPRINT_MAX_ASSETS:-512}"
MODE="${1:-report}"

usage() {
  cat <<'EOF'
Usage: check-workflow-dirty.sh [--quiet|--mark|--record-clean]

Checks only bounded workflow-owned assets. It never discovers or scans business
source roots. Exit status is 0 for dirty and 1 for clean, except --record-clean:
0 means the current bounded fingerprint was recorded and 1 means it could not be.
EOF
}

case "$MODE" in
  report|--quiet|--mark|--record-clean)
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    printf 'check-workflow-dirty: unknown option: %s\n' "$MODE" >&2
    usage >&2
    exit 2
    ;;
esac

case "$MAX_WORKFLOW_ASSETS" in
  ''|*[!0-9]*)
    MAX_WORKFLOW_ASSETS=512
    ;;
esac

mkdir -p "$STATE_DIR"

FINGERPRINT=""
ASSET_COUNT="0"
LATEST_MTIME_NS="0"

collect_fingerprint() {
  output=""
  if ! output=$(python3 - "$ROOT" "$MAX_WORKFLOW_ASSETS" <<'PY'
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
limit = int(sys.argv[2])
# Stop is a high-frequency lifecycle event.  Its automatic fingerprint is
# intentionally limited to hook-runtime, its direct planning dependency closure,
# and Graphify-stale dependencies; broad workflow docs, templates, skills, and
# eval fixtures remain explicit verification work or an explicit dirty-event
# concern. This is a source safety boundary, not a claim that those files are
# irrelevant to a release.
assets = (
    root / "AGENTS.md",
    root / ".codex/hooks.json",
    root / ".agents/references/project-conventions.md",
    root / ".agents/scripts/hook-dispatch.sh",
    root / ".agents/scripts/check-workflow-dirty.sh",
    root / ".agents/scripts/verify-workflow-smoke-fast.sh",
    root / ".agents/scripts/verify-workflow-smoke.sh",
    root / ".agents/scripts/planning-hook.py",
    root / ".agents/scripts/sensitive-command-guard.py",
    root / ".agents/scripts/sensitive_guard_policy.py",
    root / ".agents/scripts/hook_event_contract.py",
    root / ".agents/scripts/sensitive-edit-guard.py",
    root / ".agents/scripts/trajectory-monitor.py",
    root / ".agents/scripts/graphify-stale-check.sh",
    root / ".agents/scripts/portable.sh",
    root / ".agents/scripts/current_task_snapshot.py",
    root / ".agents/scripts/workflow_routing.py",
    root / ".agents/scripts/markdown_table.py",
    root / ".agents/scripts/state-compat.py",
    root / ".agents/scripts/state_compat.py",
    root / ".agents/scripts/planning-session-catchup.py",
)

digest = hashlib.sha256(b"workflow-assets-fingerprint-v1\0")
count = 0
latest_mtime_ns = 0


def add(path: Path) -> None:
    global count, latest_mtime_ns
    st = path.lstat()
    if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
        return
    count += 1
    if count > limit:
        raise RuntimeError("workflow asset count exceeds bounded limit")
    relative = path.relative_to(root).as_posix().encode("utf-8", "surrogateescape")
    digest.update(relative)
    digest.update(b"\0")
    digest.update(str(st.st_mode).encode("ascii"))
    digest.update(b"\0")
    digest.update(str(st.st_size).encode("ascii"))
    digest.update(b"\0")
    digest.update(str(st.st_mtime_ns).encode("ascii"))
    digest.update(b"\0")
    latest_mtime_ns = max(latest_mtime_ns, st.st_mtime_ns)


def on_walk_error(error: OSError) -> None:
    raise error


for asset in assets:
    try:
        mode = asset.lstat().st_mode
    except FileNotFoundError:
        continue
    if stat.S_ISDIR(mode):
        for dirpath, dirnames, filenames in os.walk(
            asset, topdown=True, followlinks=False, onerror=on_walk_error
        ):
            directory = Path(dirpath)
            for name in sorted(tuple(dirnames)):
                child = directory / name
                if child.is_symlink():
                    add(child)
                    dirnames.remove(name)
            for name in sorted(filenames):
                add(directory / name)
    else:
        add(asset)

print(f"ok {digest.hexdigest()} {count} {latest_mtime_ns}")
PY
  ); then
    return 1
  fi

  set -- $output
  if [ "$#" -ne 4 ] || [ "$1" != "ok" ]; then
    return 1
  fi
  case "$2" in
    *[!0-9a-f]*|'') return 1 ;;
  esac
  case "$3" in
    *[!0-9]*|'') return 1 ;;
  esac
  case "$4" in
    *[!0-9]*|'') return 1 ;;
  esac
  FINGERPRINT="$2"
  ASSET_COUNT="$3"
  LATEST_MTIME_NS="$4"
  return 0
}

file_mtime_ns() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).stat().st_mtime_ns)
PY
}

lookup_state_path() {
  current=$1
  legacy=$2
  if [ ! -f "$STATE_COMPAT" ] || ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi
  python3 "$STATE_COMPAT" \
    --current "$current" \
    --legacy "$legacy" \
    --deprecated-since "$STATE_COMPAT_DEPRECATED_SINCE" \
    --remove-after "$STATE_COMPAT_REMOVE_AFTER" \
    --format path
}

read_stored_fingerprint() {
  [ -f "$FINGERPRINT_FILE" ] || return 1
  stored_schema=$(awk -F= '$1 == "schema" {print $2; exit}' "$FINGERPRINT_FILE" 2>/dev/null || true)
  stored_fingerprint=$(awk -F= '$1 == "fingerprint" {print $2; exit}' "$FINGERPRINT_FILE" 2>/dev/null || true)
  stored_count=$(awk -F= '$1 == "asset_count" {print $2; exit}' "$FINGERPRINT_FILE" 2>/dev/null || true)
  if [ "$stored_schema" != "workflow-assets-fingerprint-v1" ]; then
    return 1
  fi
  case "$stored_fingerprint" in
    *[!0-9a-f]*|'') return 1 ;;
  esac
  case "$stored_count" in
    *[!0-9]*|'') return 1 ;;
  esac
  STORED_FINGERPRINT="$stored_fingerprint"
  return 0
}

record_clean_fingerprint() {
  tmp=$(mktemp "$STATE_DIR/.workflow-assets.fingerprint.XXXXXX")
  umask 077
  {
    printf 'schema=workflow-assets-fingerprint-v1\n'
    printf 'fingerprint=%s\n' "$FINGERPRINT"
    printf 'asset_count=%s\n' "$ASSET_COUNT"
    printf 'latest_mtime_ns=%s\n' "$LATEST_MTIME_NS"
    printf 'recorded_at=%s\n' "$(workflow_utc_now)"
  } > "$tmp"
  mv "$tmp" "$FINGERPRINT_FILE"
}

if [ "$MODE" = "--record-clean" ]; then
  if ! collect_fingerprint || [ "$ASSET_COUNT" -eq 0 ]; then
    printf '%s\n' "workflow fingerprint could not be recorded; workflow assets require refresh" >&2
    exit 1
  fi
  record_clean_fingerprint
  rm -f "$DIRTY_FLAG" 2>/dev/null || true
  printf '%s\n' "workflow fingerprint recorded for $ASSET_COUNT bounded workflow assets"
  exit 0
fi

dirty=0
reason=""

if [ -f "$DIRTY_FLAG" ] || [ -f "$LEGACY_DIRTY_FLAG" ]; then
  if ! selected_dirty_flag=$(lookup_state_path "$DIRTY_FLAG" "$LEGACY_DIRTY_FLAG"); then
    dirty=1
    reason="state compatibility adapter unavailable for workflow dirty flag; refresh required"
  elif [ "$selected_dirty_flag" = "$DIRTY_FLAG" ]; then
    dirty=1
    reason="current workflow dirty flag exists"
  elif [ "$selected_dirty_flag" = "$LEGACY_DIRTY_FLAG" ]; then
    dirty=1
    reason="legacy workflow dirty flag exists; migration fallback active"
  else
    dirty=1
    reason="state compatibility adapter returned an unexpected workflow dirty flag path"
  fi
elif ! collect_fingerprint; then
  dirty=1
  reason="bounded workflow asset fingerprint could not be read; refresh required"
elif [ "$ASSET_COUNT" -eq 0 ]; then
  dirty=1
  reason="no bounded workflow assets found; refresh required"
elif [ -f "$FINGERPRINT_FILE" ]; then
  if ! read_stored_fingerprint; then
    dirty=1
    reason="stored workflow fingerprint is invalid; refresh required"
  elif [ "$STORED_FINGERPRINT" != "$FINGERPRINT" ]; then
    dirty=1
    reason="bounded workflow assets changed since the recorded fingerprint"
  else
    reason="bounded workflow asset fingerprint is current"
  fi
elif [ -f "$LAST_FILE" ] || [ -f "$LEGACY_LAST_FILE" ]; then
  if ! marker=$(lookup_state_path "$LAST_FILE" "$LEGACY_LAST_FILE"); then
    dirty=1
    reason="state compatibility adapter unavailable for workflow smoke marker; refresh required"
  elif [ ! -f "$marker" ]; then
    dirty=1
    reason="state compatibility adapter returned a missing workflow smoke marker; refresh required"
  elif marker_mtime_ns=$(file_mtime_ns "$marker" 2>/dev/null) && [ "$LATEST_MTIME_NS" -le "$marker_mtime_ns" ]; then
    if [ "$marker" = "$LAST_FILE" ]; then
      marker_origin="current"
    else
      marker_origin="legacy"
    fi
    reason="$marker_origin workflow smoke marker matches bounded assets; re-run smoke to record a fingerprint"
  else
    dirty=1
    reason="bounded workflow assets are newer than the available smoke marker"
  fi
else
  dirty=1
  reason="no workflow fingerprint or successful smoke marker; refresh required"
fi

if [ "$dirty" -eq 1 ] && [ "$MODE" = "--mark" ]; then
  printf '%s %s\n' "$(workflow_utc_now)" "$reason" > "$DIRTY_FLAG"
fi

if [ "$dirty" -eq 0 ]; then
  if [ "$MODE" = "--mark" ]; then
    rm -f "$DIRTY_FLAG"
  fi
fi

if [ "$MODE" != "--quiet" ]; then
  printf '%s\n' "$reason"
fi

if [ "$dirty" -eq 1 ]; then
  exit 0
fi

exit 1
