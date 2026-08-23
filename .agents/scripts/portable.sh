#!/usr/bin/env sh

# POSIX helpers shared by base and full-profile scripts.

workflow_utc_now() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

workflow_file_mtime() {
  path=$1
  if value=$(stat -c '%Y' "$path" 2>/dev/null); then
    printf '%s\n' "$value"
    return 0
  fi
  if value=$(stat -f '%m' "$path" 2>/dev/null); then
    printf '%s\n' "$value"
    return 0
  fi
  printf 'portable: unable to read mtime: %s\n' "$path" >&2
  return 1
}

workflow_monotonic_ms() {
  # GNU date provides millisecond wall-clock values without starting an
  # interpreter. BSD date leaves `%N` literal, so validate before accepting it
  # and fall back to Python's monotonic clock there.
  if value=$(date '+%s%3N' 2>/dev/null); then
    case "$value" in
      *[!0-9]*|'') ;;
      *)
        printf '%s\n' "$value"
        return 0
        ;;
    esac
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi
  python3 - <<'PY'
import time

print(time.monotonic_ns() // 1_000_000)
PY
}

workflow_assurance_eval_inspect() {
  # Inspect leftover/source-assurance files under .agents/evals.
  # Public status:
  # 0 = leftover/source-assurance files present
  # 1 = confirmed absent (no directory, or readable tree with no files)
  # 2 = cannot inspect (unreadable entries, walk errors, missing python3)
  # Empty directories are not leftover. Walk errors and raw Python exit 1
  # are not confirmed-empty. Directory symlinks are leftover; do not follow.
  root=$1
  evals="$root/.agents/evals"
  if [ ! -d "$evals" ]; then
    return 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'cannot inspect .agents/evals: python3 is required\n' >&2
    return 2
  fi
  inspect_rc=0
  python3 - "$evals" <<'PY' || inspect_rc=$?
import os
import stat
import sys

# Internal interpreter statuses. The shell maps only 10 to public 1.
CONFIRMED_ABSENT = 10

root = sys.argv[1]
errors = []

def onerror(err):
    errors.append(err)

found = False
try:
    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror):
        for name in dirnames:
            path = os.path.join(dirpath, name)
            try:
                mode = os.lstat(path).st_mode
            except OSError as err:
                errors.append(err)
                continue
            if stat.S_ISLNK(mode):
                found = True
                break
        if found:
            break
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                mode = os.stat(path).st_mode
            except OSError as err:
                errors.append(err)
                continue
            if stat.S_ISREG(mode):
                found = True
                break
        if found:
            break
except Exception as err:
    print(f"cannot inspect .agents/evals: {err}", file=sys.stderr)
    raise SystemExit(2)

if found:
    raise SystemExit(0)
if errors:
    print(f"cannot inspect .agents/evals: {errors[0]}", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(CONFIRMED_ABSENT)
PY
  case $inspect_rc in
    0) return 0 ;;
    10) return 1 ;;
    *)
      if [ "$inspect_rc" -ne 2 ]; then
        printf 'cannot inspect .agents/evals: unexpected inspect status %s\n' "$inspect_rc" >&2
      fi
      return 2
      ;;
  esac
}
