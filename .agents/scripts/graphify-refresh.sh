#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  graphify-refresh.sh --dry-run <source-root> [...]
  graphify-refresh.sh --yes <source-root> [...]

Options:
  --dry-run       只校验参数和打印将要执行的命令，不生成图谱。
  --yes           显式确认刷新图谱。实际执行必须传入。
  -h, --help      显示帮助。

Rules:
  - <source-root> 必须是项目内真实业务源码目录。
  - 禁止直接扫描项目根目录 "."。
  - 禁止扫描 .agents、.codex、.git、graphify-out、依赖目录和构建产物。
  - 本脚本不修改 .codex/hooks.json，也不自动更新项目规则文件。
EOF
}

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/portable.sh"
GRAPHIFY_BIN="${GRAPHIFY_BIN:-graphify}"
DRY_RUN=0
CONFIRMED=0
SOURCES=()

fail() {
  printf 'graphify-refresh: %s\n' "$1" >&2
  exit "${2:-1}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes)
      CONFIRMED=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      fail "unknown option: $1" 2
      ;;
    *)
      SOURCES+=("$1")
      shift
      ;;
  esac
done

if [[ "${#SOURCES[@]}" -eq 0 ]]; then
  usage >&2
  fail "at least one <source-root> is required" 2
fi

if [[ "$DRY_RUN" -eq 1 && "$CONFIRMED" -eq 1 ]]; then
  fail "--dry-run and --yes cannot be used together" 2
fi

if [[ "$DRY_RUN" -ne 1 && "$CONFIRMED" -ne 1 ]]; then
  fail "actual refresh requires --yes; use --dry-run to preview" 2
fi

if [[ ! -f "$PROJECT_ROOT/.graphifyignore" ]]; then
  fail ".graphifyignore is required before refreshing Graphify" 2
fi

refuse_source() {
  local rel="$1"

  case "$rel" in
    ""|"."|"/")
      fail "refusing workspace root; pass one or more business source directories" 2
      ;;
    .agents|.agents/*|.codex|.codex/*|.git|.git/*|graphify-out|graphify-out/*|.codegraph|.codegraph/*|codegraph-out|codegraph-out/*)
      fail "refusing workflow or generated directory: $rel" 2
      ;;
    node_modules|node_modules/*|dist|dist/*|build|build/*|coverage|coverage/*|target|target/*)
      fail "refusing dependency, build, or coverage directory: $rel" 2
      ;;
  esac
}

has_supported_code() {
  local result
  result=$(mktemp "${TMPDIR:-/tmp}/codex-graphify-code.XXXXXX")
  if ! find "$1" -type f ! -path '*/graphify-out/*' ! -path '*/.codegraph/*' ! -path '*/codegraph-out/*' \
    \( -name '*.java' -o -name '*.kt' -o -name '*.scala' -o \
       -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' -o -name '*.vue' -o \
       -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.php' -o \
       -name '*.cs' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
    -print > "$result"; then
    rm -f "$result"
    return 2
  fi
  [[ -s "$result" ]]
  status=$?
  rm -f "$result"
  return "$status"
}

latest_source_mtime() {
  local latest files stat_mode failures
  files=$(mktemp "${TMPDIR:-/tmp}/codex-graphify-mtime.XXXXXX")
  failures=$(mktemp "${TMPDIR:-/tmp}/codex-graphify-stat-failures.XXXXXX")
  if stat -c '%Y' "$1" >/dev/null 2>&1; then
    stat_mode=gnu
  elif stat -f '%m' "$1" >/dev/null 2>&1; then
    stat_mode=bsd
  else
    rm -f "$files" "$failures"
    return 1
  fi
  : > "$failures"
  if ! find "$1" -type f ! -path '*/graphify-out/*' ! -path '*/.codegraph/*' ! -path '*/codegraph-out/*' \
    \( -name '*.java' -o -name '*.kt' -o -name '*.scala' -o \
       -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' -o -name '*.vue' -o \
       -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.php' -o \
       -name '*.cs' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
    -exec bash -c '
      mode=$1; output=$2; failures=$3; shift 3
      for file do
        if [[ "$mode" == gnu ]]; then value=$(stat -c "%Y" "$file"); else value=$(stat -f "%m" "$file"); fi
        if [[ $? -ne 0 ]] || ! printf "%s\n" "$value" >> "$output"; then
          printf "failed\n" > "$failures"
          exit 1
        fi
      done
    ' bash "$stat_mode" "$files" "$failures" {} +; then
    rm -f "$files" "$failures"
    return 1
  fi
  if [[ -s "$failures" ]]; then
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

VALIDATED=()

for src in "${SOURCES[@]}"; do
  if [[ "$src" = /* ]]; then
    candidate="$src"
  else
    candidate="$PROJECT_ROOT/$src"
  fi

  if [[ ! -d "$candidate" ]]; then
    fail "source root does not exist or is not a directory: $src" 2
  fi

  abs="$(realpath "$candidate")"

  if [[ "$abs" == "$PROJECT_ROOT" ]]; then
    fail "refusing workspace root; pass one or more business source directories" 2
  fi

  case "$abs/" in
    "$PROJECT_ROOT"/*)
      ;;
    *)
      fail "source root is outside project: $src" 2
      ;;
  esac

  rel="${abs#"$PROJECT_ROOT"/}"
  refuse_source "$rel"

  if ! has_supported_code "$abs"; then
    fail "source root has no supported code files for Graphify: $rel" 2
  fi

  VALIDATED+=("$rel")
done

resolve_graphify_bin() {
  if command -v "$GRAPHIFY_BIN" >/dev/null 2>&1; then
    command -v "$GRAPHIFY_BIN"
    return 0
  fi

  if [[ "$GRAPHIFY_BIN" == "graphify" && -x "$HOME/.local/bin/graphify" ]]; then
    printf '%s\n' "$HOME/.local/bin/graphify"
    return 0
  fi

  return 1
}

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'Dry run only. Commands that would run:\n'
  DISPLAY_BIN="$GRAPHIFY_BIN"
  if RESOLVED_BIN="$(resolve_graphify_bin)"; then
    DISPLAY_BIN="$RESOLVED_BIN"
  fi
  for rel in "${VALIDATED[@]}"; do
    printf '  (cd %s && %s update %s)\n' "$PROJECT_ROOT" "$DISPLAY_BIN" "$rel"
  done
  exit 0
fi

if ! RESOLVED_BIN="$(resolve_graphify_bin)"; then
  fail "graphify command not found; install Graphify first or set GRAPHIFY_BIN" 127
fi

mkdir -p "$PROJECT_ROOT/graphify-out"
METADATA="$PROJECT_ROOT/graphify-out/REFRESH_METADATA.md"
TMP_METADATA="$METADATA.tmp"

{
  printf '# Graphify Refresh Metadata\n\n'
  printf -- '- Generated at: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf -- '- Command: `%s`\n' "$0 --yes ${VALIDATED[*]}"
  printf -- '- Source roots:\n'
  for rel in "${VALIDATED[@]}"; do
    printf -- '  - `%s`\n' "$rel"
  done
  printf -- '- Source snapshots:\n'
  for rel in "${VALIDATED[@]}"; do
    if ! snapshot=$(latest_source_mtime "$PROJECT_ROOT/$rel"); then
      rm -f "$TMP_METADATA"
      fail "unable to read complete source mtime snapshot for $rel" 2
    fi
    printf -- '  - `%s`: `%s`\n' "$rel" "$snapshot"
  done
  printf '\n'
  printf 'After a successful refresh, update `.agents/references/project-conventions.md` manually:\n'
  printf -- '- Graphify status: `enabled-fresh`\n'
  printf -- '- Source roots: match the list above\n'
  printf -- '- Last generated: match the timestamp above\n'
} > "$TMP_METADATA"

for rel in "${VALIDATED[@]}"; do
  printf 'Running: %s update %s\n' "$RESOLVED_BIN" "$rel"
  (cd "$PROJECT_ROOT" && "$RESOLVED_BIN" update "$rel")
done

AGG_REPORT="$PROJECT_ROOT/graphify-out/GRAPH_REPORT.md"

{
  printf '# Graphify Aggregate Report\n\n'
  printf -- '- Generated at: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf -- '- Source roots:\n'
  for rel in "${VALIDATED[@]}"; do
    printf -- '  - `%s`\n' "$rel"
  done
  printf '\n'
  printf '## Source Reports\n'
  for rel in "${VALIDATED[@]}"; do
    report="$PROJECT_ROOT/$rel/graphify-out/GRAPH_REPORT.md"
    graph="$PROJECT_ROOT/$rel/graphify-out/graph.json"
    if [[ -s "$report" && -s "$graph" ]]; then
      printf -- '- `%s`: `%s`, `%s`\n' "$rel" "$rel/graphify-out/GRAPH_REPORT.md" "$rel/graphify-out/graph.json"
    else
      printf -- '- `%s`: missing report or graph output\n' "$rel"
    fi
  done
  printf '\n'
  printf 'Use this aggregate report as an index. For detailed structure, read the source-specific `GRAPH_REPORT.md` files only when the task needs that source root.\n'
} > "$AGG_REPORT"

mv "$TMP_METADATA" "$METADATA"
printf 'Graphify refresh metadata written to %s\n' "$METADATA"
printf 'Graphify aggregate report written to %s\n' "$AGG_REPORT"
