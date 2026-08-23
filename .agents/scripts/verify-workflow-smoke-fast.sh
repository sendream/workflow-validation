#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/.agents/scripts/portable.sh"
FAILURES=0
SMOKE_TMP="$(mktemp -d)"
trap 'rm -rf "$SMOKE_TMP"' EXIT

pass() {
  printf 'pass: %s\n' "$1"
}

fail() {
  printf 'fail: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

require_file() {
  if [[ -f "$ROOT/$1" ]]; then
    pass "file exists: $1"
  else
    fail "missing file: $1"
  fi
}

require_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"

  if grep -Eq -- "$pattern" "$ROOT/$file"; then
    pass "$label"
  else
    fail "$label"
  fi
}

python_syntax_check() {
  python3 - "$@" <<'PY'
import ast
import pathlib
import sys

for filename in sys.argv[1:]:
    source = pathlib.Path(filename).read_text(encoding="utf-8")
    ast.parse(source, filename=filename)
PY
}

require_file "AGENTS.md"
require_file ".codex/hooks.json"
require_file ".agents/scripts/verify-workflow-smoke.sh"
require_file ".agents/scripts/sensitive-command-guard.py"
require_file ".agents/scripts/sensitive_guard_policy.py"
require_file ".agents/scripts/verify-hooks-runtime.sh"

require_contains ".agents/scripts/verify-workflow-smoke.sh" 'base-authoritative-smoke-20260611' "base workflow smoke marker is current"

if python3 -m json.tool "$ROOT/.codex/hooks.json" >/dev/null; then
  pass ".codex/hooks.json is valid JSON"
else
  fail ".codex/hooks.json is valid JSON"
fi

if python_syntax_check "$ROOT/.agents/scripts/sensitive-command-guard.py" "$ROOT/.agents/scripts/sensitive_guard_policy.py"; then
  pass "sensitive command guard and policy syntax"
else
  fail "sensitive command guard and policy syntax"
fi

if sh -n "$ROOT/.agents/scripts/verify-hooks-runtime.sh"; then
  pass "verify-hooks-runtime.sh syntax"
else
  fail "verify-hooks-runtime.sh syntax"
fi

if [[ -f "$ROOT/.agents/scripts/hook-dispatch.sh" ]]; then
  if sh -n "$ROOT/.agents/scripts/hook-dispatch.sh"; then
    pass "hook-dispatch.sh syntax"
  else
    fail "hook-dispatch.sh syntax"
  fi
fi

if [[ -f "$ROOT/.agents/scripts/check-workflow-dirty.sh" ]]; then
  if sh -n "$ROOT/.agents/scripts/check-workflow-dirty.sh"; then
    pass "check-workflow-dirty.sh syntax"
  else
    fail "check-workflow-dirty.sh syntax"
  fi

  dirty_tmp="$SMOKE_TMP/dirty-project"
  mkdir -p "$dirty_tmp/.agents/scripts" "$dirty_tmp/.agent-state/flags"
  cp "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$dirty_tmp/.agents/scripts/"
  workflow_utc_now > "$dirty_tmp/.agent-state/flags/workflow-smoke.last"
  sleep 1
  touch "$dirty_tmp/.agents/scripts/check-workflow-dirty.sh"
  if sh "$dirty_tmp/.agents/scripts/check-workflow-dirty.sh" --quiet >/dev/null; then
    pass "workflow dirty checker detects workflow asset changes"
  else
    fail "workflow dirty checker detects workflow asset changes"
  fi
fi

if [[ -f "$ROOT/.agents/scripts/planning-hook.py" ]]; then
  if python_syntax_check "$ROOT/.agents/scripts/planning-hook.py"; then
    pass "planning-hook.py syntax"
  else
    fail "planning-hook.py syntax"
  fi

  plan_tmp="$SMOKE_TMP/template-inactive"
  mkdir -p "$plan_tmp"
  cat > "$plan_tmp/task_plan.md" <<'EOF'
# Task Plan

## Task
一句话说明这次任务要解决什么问题。

## Current phase
- 阶段：理解中 / 规划中 / 执行中 / 验证中 / 收口中 / 已完成

## Traceability
- Active task id：optional / 待填写
EOF
  printf '# Progress\n\n## Review / Audit Boundary\n| item | value |\n|---|---|\n| Mode | review-only |\n' > "$plan_tmp/progress.md"
  printf '# Findings\n' > "$plan_tmp/findings.md"
  post_bash_output="$(python3 "$ROOT/.agents/scripts/planning-hook.py" post-bash "$plan_tmp")"
  if [[ -z "$post_bash_output" ]]; then
    pass "planning hook treats raw template/review-only records as inactive"
  else
    fail "planning hook treats raw template/review-only records as inactive"
  fi
fi

if [[ "$FAILURES" -gt 0 ]]; then
  printf '\nFast smoke failed: %d failure(s)\n' "$FAILURES" >&2
  exit 1
fi

printf '\nFast smoke passed\n'
