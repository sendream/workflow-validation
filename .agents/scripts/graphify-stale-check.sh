#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
# ROOT must be physical (pwd -P): source roots are canonicalized with pwd -P
# below, and a logical ROOT (e.g. macOS /var -> /private/var, or a symlinked
# checkout) would make the prefix containment check report a false stale.
ROOT=$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd -P)
. "$SCRIPT_DIR/portable.sh"
STATE_DIR="$ROOT/.agent-state/flags"
FLAG_FILE="$STATE_DIR/graphify-stale.flag"
LAST_FILE="$STATE_DIR/graphify-stale.last"
CONVENTIONS="$ROOT/.agents/references/project-conventions.md"
METADATA="$ROOT/graphify-out/REFRESH_METADATA.md"
MODE_REPORT=1
MODE_MARK=0
TRIGGER="manual"

usage() {
  cat <<'EOF'
Usage:
  graphify-stale-check.sh [--quiet] [--mark] [--workflow-dirty-event]

Options:
  --quiet   不输出普通文本，只通过退出码表达状态。
  --mark    把 stale/fresh 检查结果写入 .agent-state/flags/。
  --workflow-dirty-event 记录本次检查由已检测到的 workflow asset 变化触发。

Rules:
  - 只检查 Graphify 是否可能过期，不生成图谱。
  - 只有项目 Graphify 状态为 enabled-fresh 时才检查 source roots。
  - 返回 0 表示 fresh 或跳过；返回 1 表示 stale。
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --quiet)
      MODE_REPORT=0
      shift
      ;;
    --mark)
      MODE_MARK=1
      shift
      ;;
    --workflow-dirty-event)
      TRIGGER="workflow-dirty-event"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'graphify-stale-check: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

say() {
  if [ "$MODE_REPORT" -eq 1 ]; then
    printf '%s\n' "$1"
  fi
}

mark_result() {
  status=$1
  reason=$2

  if [ "$TRIGGER" = "workflow-dirty-event" ]; then
    reason="$reason [trigger=workflow-dirty-event]"
  fi

  if [ "$MODE_MARK" -ne 1 ]; then
    return 0
  fi

  mkdir -p "$STATE_DIR"
  printf '%s %s\n' "$(workflow_utc_now)" "$reason" > "$LAST_FILE"

  if [ "$status" = "stale" ]; then
    printf '%s %s\n' "$(workflow_utc_now)" "$reason" > "$FLAG_FILE"
  else
    rm -f "$FLAG_FILE"
  fi
}

is_enabled_fresh() {
  [ -f "$CONVENTIONS" ] && grep -Eq '状态：enabled-fresh|当前状态：enabled-fresh' "$CONVENTIONS"
}

supported_newer_file() {
  dir=$1
  find "$dir" -type f ! -path '*/graphify-out/*' \
    \( -name '*.java' -o -name '*.kt' -o -name '*.scala' -o \
       -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' -o -name '*.vue' -o \
       -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.php' -o \
       -name '*.cs' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
    -newer "$METADATA" -print
}

latest_source_mtime() {
  dir=$1
  files=$(mktemp "${TMPDIR:-/tmp}/codex-graphify-mtime.XXXXXX")
  failures=$(mktemp "${TMPDIR:-/tmp}/codex-graphify-stat-failures.XXXXXX")
  if stat -c '%Y' "$dir" >/dev/null 2>&1; then
    stat_mode=gnu
  elif stat -f '%m' "$dir" >/dev/null 2>&1; then
    stat_mode=bsd
  else
    rm -f "$files" "$failures"
    return 1
  fi
  : > "$failures"
  if ! find "$dir" -type f ! -path '*/graphify-out/*' \
    \( -name '*.java' -o -name '*.kt' -o -name '*.scala' -o \
       -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' -o -name '*.vue' -o \
       -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.php' -o \
       -name '*.cs' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
    -exec sh -c '
      mode=$1; output=$2; failures=$3; shift 3
      for file do
        if [ "$mode" = gnu ]; then value=$(stat -c "%Y" "$file"); else value=$(stat -f "%m" "$file"); fi
        if [ $? -ne 0 ] || ! printf "%s\n" "$value" >> "$output"; then
          printf "failed\n" > "$failures"
          exit 1
        fi
      done
    ' sh "$stat_mode" "$files" "$failures" {} +; then
    rm -f "$files" "$failures"
    return 1
  fi
  if [ -s "$failures" ]; then
    rm -f "$files" "$failures"
    return 1
  fi
  rm -f "$failures"
  if grep -Evq '^[0-9]+$' "$files"; then
    rm -f "$files"
    return 1
  fi
  latest=$(awk 'BEGIN { max=0 } $1 > max { max=$1 } END { print max }' "$files")
  rm -f "$files"
  printf '%s\n' "$latest"
}

snapshot_epoch() {
  rel=$1
  awk -v rel="$rel" '
    /^  - `.*`: `[0-9]+`$/ {
      line = $0
      sub(/^  - `/, "", line)
      split(line, parts, "`: `")
      if (parts[1] == rel) {
        sub(/`$/, "", parts[2])
        print parts[2]
        exit
      }
    }
  ' "$METADATA"
}

if ! is_enabled_fresh; then
  reason="Graphify stale check skipped: status is not enabled-fresh"
  mark_result "fresh" "$reason"
  say "$reason"
  exit 0
fi

if [ ! -s "$METADATA" ]; then
  reason="Graphify stale: refresh metadata is missing"
  mark_result "stale" "$reason"
  say "$reason"
  exit 1
fi

roots_tmp=$(mktemp)
trap 'rm -f "$roots_tmp"' EXIT INT TERM

sed -n 's/^  - `\([^`][^`]*\)`$/\1/p' "$METADATA" > "$roots_tmp"

if [ ! -s "$roots_tmp" ]; then
  reason="Graphify stale: source roots are missing from refresh metadata"
  mark_result "stale" "$reason"
  say "$reason"
  exit 1
fi

while IFS= read -r rel; do
  [ -n "$rel" ] || continue

  case "$rel" in
    ""|"."|"/"|.agents|.agents/*|.codex|.codex/*|.git|.git/*|graphify-out|graphify-out/*)
      reason="Graphify stale: unsafe source root in metadata: $rel"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
      ;;
  esac

  abs="$ROOT/$rel"
  if [ ! -d "$abs" ]; then
    reason="Graphify stale: source root missing: $rel"
    mark_result "stale" "$reason"
    say "$reason"
    exit 1
  fi
  if ! abs=$(CDPATH= cd "$abs" 2>/dev/null && pwd -P); then
    reason="Graphify stale: unable to resolve source root: $rel"
    mark_result "stale" "$reason"
    say "$reason"
    exit 1
  fi
  case "$abs/" in
    "$ROOT"/*) ;;
    *)
      reason="Graphify stale: source root resolves outside project: $rel"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
      ;;
  esac

  snapshot=$(snapshot_epoch "$rel")
  if [ -n "$snapshot" ]; then
    if ! current=$(latest_source_mtime "$abs"); then
      reason="Graphify stale: unable to read source mtime for $rel"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
    fi
    if [ "$current" -gt "$snapshot" ]; then
      reason="Graphify stale: $rel source mtime $current is newer than snapshot $snapshot"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
    fi
  else
    if ! newer=$(supported_newer_file "$abs"); then
      reason="Graphify stale: unable to scan source files for $rel"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
    fi
    if [ -n "$newer" ]; then
      reason="Graphify stale: $newer is newer than $METADATA"
      mark_result "stale" "$reason"
      say "$reason"
      exit 1
    fi
  fi
done < "$roots_tmp"

reason="Graphify fresh: source roots are not newer than refresh metadata"
mark_result "fresh" "$reason"
say "$reason"
exit 0
