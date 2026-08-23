#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILURES=0
SMOKE_TMP="$(mktemp -d)"
trap 'rm -rf "$SMOKE_TMP"' EXIT
VALIDATION_LAYER="runtime-smoke"

usage() {
  cat <<'EOF'
Usage: verify-workflow-smoke-full.sh [--layer runtime-smoke]

This is the runtime-smoke layer. It validates a full applied overlay, hook
protocol, and installation-facing behavior. Static package contracts belong to
verify-workflow-smoke.sh --layer package-contract.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --layer)
      shift
      if [[ $# -eq 0 ]]; then
        printf 'missing value for --layer\n' >&2
        usage >&2
        exit 2
      fi
      VALIDATION_LAYER="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$VALIDATION_LAYER" != "runtime-smoke" ]]; then
  printf 'unknown validation layer: %s\n' "$VALIDATION_LAYER" >&2
  usage >&2
  exit 2
fi

printf 'layer runtime-smoke: start\n'

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

if [[ "${WORKFLOW_BASE_SMOKE_ALREADY_RUN:-0}" == "1" ]]; then
  pass "base workflow smoke already owned by the source self-check"
elif [[ -x "$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh" ]]; then
  if "$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh"; then
    pass "bounded installation preflight passes before full-only runtime checks"
  else
    fail "bounded installation preflight passes before full-only runtime checks"
  fi
else
  fail "bounded installation preflight is missing or not executable"
fi

require_file ".agents/scripts/verify-workflow-smoke-fast.sh"
require_file ".agents/scripts/hook-dispatch.sh"
require_file ".agents/scripts/portable.sh"
require_file ".agents/scripts/verify-hooks-runtime.sh"
require_file ".agents/scripts/check-workflow-dirty.sh"
require_file ".agents/scripts/planning-hook.py"
require_file ".agents/scripts/current_task_snapshot.py"
require_file ".agents/scripts/state_compat.py"
require_file ".agents/scripts/verify-planning-hook-protocol.py"
require_file ".agents/scripts/planning-session-catchup.py"
require_file ".agents/scripts/planning-status.sh"
require_file ".agents/scripts/planning-check-complete.sh"
require_file ".agents/scripts/sensitive_guard_policy.py"
require_file ".agents/scripts/hook_event_contract.py"
require_file ".agents/scripts/sensitive-edit-guard.py"
require_file ".agents/scripts/trajectory-monitor.py"
require_file ".agents/templates/task_archive.md"
require_file ".codex/hooks.json"

if bash -n "$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh"; then
  pass "verify-workflow-smoke-fast.sh syntax"
else
  fail "verify-workflow-smoke-fast.sh syntax"
fi

if [[ -x "$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh" ]]; then
  pass "verify-workflow-smoke-fast.sh executable"
else
  fail "verify-workflow-smoke-fast.sh executable"
fi

if sh -n "$ROOT/.agents/scripts/hook-dispatch.sh"; then
  pass "hook-dispatch.sh syntax"
else
  fail "hook-dispatch.sh syntax"
fi

require_contains ".agents/scripts/hook-dispatch.sh" 'verify-workflow-smoke-fast\.sh' "Stop hook uses fast workflow smoke path"
require_contains ".agents/scripts/hook-dispatch.sh" 'hook-telemetry\.last' "hook dispatcher records redacted report-only telemetry"
require_contains ".agents/scripts/check-workflow-dirty.sh" 'workflow-assets\.fingerprint' "dirty checker uses a bounded workflow fingerprint"

if (
  fixture="$SMOKE_TMP/stop-fast-fixture"
  mkdir -p "$fixture/.agents/scripts" "$fixture/.agent-state/flags"
  cp "$ROOT/.agents/scripts/hook-dispatch.sh" "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$fixture/.agents/scripts/"
  cat > "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" <<'EOF'
#!/usr/bin/env bash
printf 'fast-runner-sentinel\n'
EOF
  cat > "$fixture/.agents/scripts/verify-workflow-smoke.sh" <<'EOF'
#!/usr/bin/env bash
printf 'base-runner-sentinel\n'
EOF
  chmod +x "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" "$fixture/.agents/scripts/verify-workflow-smoke.sh"
  printf 'dirty\n' > "$fixture/.agent-state/flags/workflow-dirty.flag"
  printf '{}\n' | sh "$fixture/.agents/scripts/hook-dispatch.sh" stop > "$fixture/stop-output.json"
  grep -q 'fast-runner-sentinel' "$fixture/.agent-state/flags/latest-smoke.log" &&
    test -f "$fixture/.agent-state/flags/workflow-smoke.last" &&
    test -f "$fixture/.agent-state/flags/workflow-assets.fingerprint" &&
    test ! -f "$fixture/.agent-state/flags/workflow-dirty.flag" &&
    test ! -s "$fixture/stop-output.json"
); then
  pass "Stop hook dispatches dirty workflow smoke to fast runner"
else
  fail "Stop hook dispatches dirty workflow smoke to fast runner"
fi

if (
  fixture="$SMOKE_TMP/stop-fallback-fixture"
  mkdir -p "$fixture/.agents/scripts" "$fixture/.agent-state/flags"
  cp "$ROOT/.agents/scripts/hook-dispatch.sh" "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$fixture/.agents/scripts/"
  cat > "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" <<'EOF'
#!/usr/bin/env bash
printf 'fast-runner-should-not-run\n'
EOF
  cat > "$fixture/.agents/scripts/verify-workflow-smoke.sh" <<'EOF'
#!/usr/bin/env bash
printf 'base-runner-sentinel\n'
EOF
  chmod 0644 "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh"
  chmod +x "$fixture/.agents/scripts/verify-workflow-smoke.sh"
  printf 'dirty\n' > "$fixture/.agent-state/flags/workflow-dirty.flag"
  printf '{}\n' | sh "$fixture/.agents/scripts/hook-dispatch.sh" stop > "$fixture/stop-output.json"
  grep -q 'base-runner-sentinel' "$fixture/.agent-state/flags/latest-smoke.log" &&
    test -f "$fixture/.agent-state/flags/workflow-smoke.last" &&
    test -f "$fixture/.agent-state/flags/workflow-assets.fingerprint" &&
    test ! -f "$fixture/.agent-state/flags/workflow-dirty.flag"
); then
  pass "Stop hook falls back to base smoke when fast runner is not executable"
else
  fail "Stop hook falls back to base smoke when fast runner is not executable"
fi

if (
  fixture="$SMOKE_TMP/stop-failure-fixture"
  mkdir -p "$fixture/.agents/scripts" "$fixture/.agent-state/flags"
  cp "$ROOT/.agents/scripts/hook-dispatch.sh" "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$fixture/.agents/scripts/"
  cat > "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" <<'EOF'
#!/usr/bin/env bash
printf 'fast-runner-failed\n'
exit 7
EOF
  cat > "$fixture/.agents/scripts/verify-workflow-smoke.sh" <<'EOF'
#!/usr/bin/env bash
printf 'base-runner-should-not-run\n'
EOF
  chmod +x "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" "$fixture/.agents/scripts/verify-workflow-smoke.sh"
  printf 'dirty\n' > "$fixture/.agent-state/flags/workflow-dirty.flag"
  printf '{}\n' | sh "$fixture/.agents/scripts/hook-dispatch.sh" stop > "$fixture/stop-output.json"
  grep -q 'fast-runner-failed' "$fixture/.agent-state/flags/latest-smoke.log" &&
    test -f "$fixture/.agent-state/flags/workflow-dirty.flag" &&
    grep -q 'Stop workflow smoke failed' "$fixture/stop-output.json" &&
    python3 -m json.tool "$fixture/stop-output.json" >/dev/null
); then
  pass "Stop hook reports failed smoke with JSON systemMessage and log path"
else
  fail "Stop hook reports failed smoke with JSON systemMessage and log path"
fi

if (
  fixture="$SMOKE_TMP/stop-stale-lock-fixture"
  mkdir -p "$fixture/.agents/scripts" "$fixture/.agent-state/flags/workflow.lock"
  cp "$ROOT/.agents/scripts/hook-dispatch.sh" "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$fixture/.agents/scripts/"
  cat > "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" <<'EOF'
#!/usr/bin/env bash
printf 'fast-runner-after-stale-lock\n'
EOF
  cat > "$fixture/.agents/scripts/verify-workflow-smoke.sh" <<'EOF'
#!/usr/bin/env bash
printf 'base-runner-should-not-run\n'
EOF
  chmod +x "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" "$fixture/.agents/scripts/verify-workflow-smoke.sh"
  printf '999999\n' > "$fixture/.agent-state/flags/workflow.lock/pid"
  python3 - "$fixture/.agent-state/flags/workflow.lock" <<'PY'
import os, sys
os.utime(sys.argv[1], (1, 1))
PY
  printf 'dirty\n' > "$fixture/.agent-state/flags/workflow-dirty.flag"
  printf '{}\n' | CODEX_WORKFLOW_LOCK_STALE_SECONDS=1 sh "$fixture/.agents/scripts/hook-dispatch.sh" stop > "$fixture/stop-output.json"
  grep -q 'fast-runner-after-stale-lock' "$fixture/.agent-state/flags/latest-smoke.log" &&
    test -f "$fixture/.agent-state/flags/workflow-smoke.last" &&
    test ! -f "$fixture/.agent-state/flags/workflow-dirty.flag" &&
    test ! -d "$fixture/.agent-state/flags/workflow.lock"
); then
  pass "Stop hook clears stale workflow lock and runs smoke"
else
  fail "Stop hook clears stale workflow lock and runs smoke"
fi

if (
  fixture="$SMOKE_TMP/stop-failure-no-python-fixture"
  mkdir -p "$fixture/.agents/scripts" "$fixture/.agent-state/flags" "$fixture/bin"
  cp "$ROOT/.agents/scripts/hook-dispatch.sh" "$ROOT/.agents/scripts/portable.sh" "$fixture/.agents/scripts/"
  cat > "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" <<'EOF'
#!/usr/bin/env bash
printf 'fast-runner-failed-without-python\n'
exit 7
EOF
  cat > "$fixture/.agents/scripts/verify-workflow-smoke.sh" <<'EOF'
#!/usr/bin/env bash
printf 'base-runner-should-not-run\n'
EOF
  chmod +x "$fixture/.agents/scripts/verify-workflow-smoke-fast.sh" "$fixture/.agents/scripts/verify-workflow-smoke.sh"
  for cmd in bash cat date dirname mkdir mktemp pwd rm rmdir stat; do
    ln -s "$(command -v "$cmd")" "$fixture/bin/$cmd"
  done
  printf 'dirty\n' > "$fixture/.agent-state/flags/workflow-dirty.flag"
  PATH="$fixture/bin" /bin/sh "$fixture/.agents/scripts/hook-dispatch.sh" stop > "$fixture/stop-output.json" <<'EOF'
{}
EOF
  grep -q 'fast-runner-failed-without-python' "$fixture/.agent-state/flags/latest-smoke.log" &&
    test -f "$fixture/.agent-state/flags/workflow-dirty.flag" &&
    grep -q 'Stop workflow smoke failed' "$fixture/stop-output.json" &&
    python3 -m json.tool "$fixture/stop-output.json" >/dev/null
); then
  pass "Stop hook emits smoke failure JSON without python3"
else
  fail "Stop hook emits smoke failure JSON without python3"
fi

if sh -n "$ROOT/.agents/scripts/verify-hooks-runtime.sh"; then
  pass "verify-hooks-runtime.sh syntax"
else
  fail "verify-hooks-runtime.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/check-workflow-dirty.sh"; then
  pass "check-workflow-dirty.sh syntax"
else
  fail "check-workflow-dirty.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/planning-status.sh"; then
  pass "planning-status.sh syntax"
else
  fail "planning-status.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/planning-check-complete.sh"; then
  pass "planning-check-complete.sh syntax"
else
  fail "planning-check-complete.sh syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/planning-hook.py" "$ROOT/.agents/scripts/current_task_snapshot.py" "$ROOT/.agents/scripts/state_compat.py" "$ROOT/.agents/scripts/verify-planning-hook-protocol.py" "$ROOT/.agents/scripts/planning-session-catchup.py"; then
  pass "planning hook python syntax"
else
  fail "planning hook python syntax"
fi

if python3 "$ROOT/.agents/scripts/verify-planning-hook-protocol.py" --root "$ROOT"; then
  pass "planning hook protocol passes with PTY stdin held open"
else
  fail "planning hook protocol passes with PTY stdin held open"
fi

if (
  mkdir -p "$SMOKE_TMP/template-inactive"
  cat > "$SMOKE_TMP/template-inactive/task_plan.md" <<'EOF'
# Task Plan

## Task
一句话说明这次任务要解决什么问题。

## Current phase
- 阶段：理解中 / 规划中 / 执行中 / 验证中 / 收口中 / 已完成

## Traceability
- Active task id：optional / 待填写
EOF
  printf '# Progress\n\n## Review / Audit Boundary\n| item | value |\n|---|---|\n| Mode | review-only |\n' > "$SMOKE_TMP/template-inactive/progress.md"
  printf '# Findings\n' > "$SMOKE_TMP/template-inactive/findings.md"
	  status_output="$(python3 "$ROOT/.agents/scripts/planning-hook.py" status "$SMOKE_TMP/template-inactive")"
	  complete_output="$(python3 "$ROOT/.agents/scripts/planning-hook.py" check-complete "$SMOKE_TMP/template-inactive")"
	  post_bash_output="$(python3 "$ROOT/.agents/scripts/planning-hook.py" post-bash "$SMOKE_TMP/template-inactive")"
	  test -z "$post_bash_output" &&
	    printf '%s\n%s\n' "$status_output" "$complete_output" | grep -Eq 'No active task_plan\.md|template placeholder is inactive|review-only / plan-only'
	); then
  pass "planning hook treats raw template/review-only records as inactive"
else
  fail "planning hook treats raw template/review-only records as inactive"
fi

if "$ROOT/.agents/scripts/verify-hooks-runtime.sh" --fail-on-broken "$ROOT"; then
  pass "hooks runtime config is not broken; degraded status may require project trust or Codex hooks feature flag"
else
  fail "hooks runtime config is not broken"
fi

if python3 - "$ROOT/.codex/hooks.json" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
hooks = payload.get("hooks", {})

assert "SessionStart" in hooks
assert "UserPromptSubmit" in hooks
assert "PreToolUse" in hooks
assert "PostToolUse" in hooks
assert "Stop" in hooks

pretool = hooks["PreToolUse"]
assert any(row.get("matcher") == "Bash" for row in pretool)
assert any(row.get("matcher") == "apply_patch" for row in pretool)
posttool = hooks["PostToolUse"]
assert any(row.get("matcher") == "Bash" for row in posttool)
assert any(row.get("matcher") == "apply_patch" for row in posttool)
for entries in hooks.values():
    assert "CODEX_WORKFLOW_HOOK_PRESET=full" in entries[0]["hooks"][0]["command"]

print("hooks-json-ok")
PY
then
  pass "hooks JSON contains expected full profile hooks"
else
  fail "hooks JSON contains expected full profile hooks"
fi

if (
  mkdir -p "$SMOKE_TMP/project/.agents/scripts" "$SMOKE_TMP/project/.agent-state/flags"
  cp "$ROOT/.agents/scripts/check-workflow-dirty.sh" "$ROOT/.agents/scripts/portable.sh" "$SMOKE_TMP/project/.agents/scripts/"
  sh "$SMOKE_TMP/project/.agents/scripts/check-workflow-dirty.sh" --record-clean >/dev/null
  python3 - "$SMOKE_TMP/project/.agents/scripts/check-workflow-dirty.sh" <<'PY'
import os, pathlib, sys
path = pathlib.Path(sys.argv[1])
before = path.stat().st_mtime_ns
second = before - (before % 1_000_000_000)
after = second + 900_000_000
if after == before:
    after = second + 100
os.utime(path, ns=(after, after))
PY
  sh "$SMOKE_TMP/project/.agents/scripts/check-workflow-dirty.sh" --quiet >/dev/null
); then
  pass "workflow dirty checker detects same-second workflow asset changes"
else
  fail "workflow dirty checker detects same-second workflow asset changes"
fi

require_contains ".agents/templates/task_archive.md" 'archive-ready' "full profile preserves archive staging rule"
require_contains ".agents/skills/planning-with-files/SKILL.md" 'scope.*compatibility-only' "full profile preserves the planning wrapper compatibility boundary"
require_contains ".agents/skills/planning-with-files/SKILL.md" 'negative_trigger.*every new task' "full profile keeps new tasks off the planning wrapper"
require_contains ".agents/templates/task_plan.md" 'Tier：待填写' "full profile preserves template placeholder-safe risk tier"

if [[ "$FAILURES" -eq 0 ]]; then
  printf 'layer runtime-smoke: pass\n'
  printf 'full workflow smoke passed\n'
else
  printf 'layer runtime-smoke: fail\n' >&2
  printf 'full workflow smoke failed: %s failure(s)\n' "$FAILURES" >&2
fi

exit "$FAILURES"
