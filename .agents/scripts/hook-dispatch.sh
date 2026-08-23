#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)
. "$SCRIPT_DIR/portable.sh"
STATE_DIR="$ROOT/.agent-state/flags"
LEGACY_STATE_DIR="$ROOT/.agents/state"
LOCK_DIR="$STATE_DIR/workflow.lock"
LOCK_PID_FILE="$LOCK_DIR/pid"
LOCK_CREATED_FILE="$LOCK_DIR/created_at"
LOCK_STALE_SECONDS="${CODEX_WORKFLOW_LOCK_STALE_SECONDS:-600}"
DIRTY_FLAG="$STATE_DIR/workflow-dirty.flag"
LEGACY_DIRTY_FLAG="$LEGACY_STATE_DIR/workflow-dirty.flag"
LAST_FILE="$STATE_DIR/workflow-smoke.last"
LOG_FILE="$STATE_DIR/latest-smoke.log"
BUSY_SKIP_FILE="$STATE_DIR/hook-skipped-busy.last"
TELEMETRY_FILE="$STATE_DIR/hook-telemetry.last"
RUNNER="$ROOT/.agents/scripts/verify-workflow-smoke.sh"
FAST_RUNNER="$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh"
DIRTY_CHECKER="$ROOT/.agents/scripts/check-workflow-dirty.sh"
STALE_CHECKER="$ROOT/.agents/scripts/graphify-stale-check.sh"
PLANNING_HOOK="$ROOT/.agents/scripts/planning-hook.py"
SENSITIVE_GUARD="$ROOT/.agents/scripts/sensitive-command-guard.py"
SENSITIVE_EDIT_GUARD="$ROOT/.agents/scripts/sensitive-edit-guard.py"
TRAJECTORY_MONITOR="$ROOT/.agents/scripts/trajectory-monitor.py"
EVENT="${1:-}"
HOOK_PRESET="${CODEX_WORKFLOW_HOOK_PRESET:-full}"
STOP_SMOKE_MESSAGE=""
LOCK_ACQUIRED=0
LOCK_OUTCOME="not-required"
RESULT_CLASS="ok"
SCAN_SCOPE="none"
STATE_BYTES_READ="unavailable"
HOOK_STARTED_AT_MS=$(workflow_monotonic_ms 2>/dev/null || printf 'unavailable')

case "$HOOK_PRESET" in
  full|assist)
    ;;
  *)
    HOOK_PRESET="unknown"
    ;;
esac

case "$EVENT" in
  session-start|user-prompt|pre-bash|post-bash|pre-edit|post-edit|stop)
    TELEMETRY_EVENT="$EVENT"
    ;;
  *)
    TELEMETRY_EVENT="unsupported"
    ;;
esac

case "$EVENT" in
  session-start) EVENT_BUDGET_MS=800 ;;
  user-prompt|post-bash|post-edit) EVENT_BUDGET_MS=500 ;;
  pre-bash|pre-edit) EVENT_BUDGET_MS=300 ;;
  stop) EVENT_BUDGET_MS=3000 ;;
  *) EVENT_BUDGET_MS="unavailable" ;;
esac

mkdir -p "$STATE_DIR"

# Codex hooks treat stdout as protocol output. Keep stdout empty unless we
# intentionally return valid hook JSON.
PAYLOAD_FILE=$(mktemp)
case "$EVENT" in
  pre-bash|post-bash|pre-edit|post-edit|stop)
    cat > "$PAYLOAD_FILE" || true
    ;;
  *)
    : > "$PAYLOAD_FILE"
    ;;
esac

cleanup() {
  rm -f "$PAYLOAD_FILE"
  if [ "$LOCK_ACQUIRED" -eq 1 ]; then
    rm -f "$LOCK_PID_FILE" "$LOCK_CREATED_FILE" 2>/dev/null || true
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

record_hook_telemetry() {
  timestamp=$(workflow_utc_now 2>/dev/null || printf 'unknown')
  command_duration_ms="unavailable"
  case "$HOOK_STARTED_AT_MS" in
    ''|*[!0-9]*)
      ;;
    *)
      hook_finished_at_ms=$(workflow_monotonic_ms 2>/dev/null || printf '')
      case "$hook_finished_at_ms" in
        ''|*[!0-9]*)
          ;;
        *)
          if [ "$hook_finished_at_ms" -ge "$HOOK_STARTED_AT_MS" ]; then
            command_duration_ms=$((hook_finished_at_ms - HOOK_STARTED_AT_MS))
          fi
          ;;
      esac
      ;;
  esac
  if ! command -v mv >/dev/null 2>&1; then
    return 0
  fi
  if ! tmp=$(mktemp "$STATE_DIR/.hook-telemetry.XXXXXX"); then
    return 0
  fi
  if ! {
    printf '{"timestamp":"%s","event":"%s","preset":"%s","event_budget_ms":"%s","state_bytes_read":"%s","scan_scope":"%s","lock_outcome":"%s","command_duration_ms":"%s","result_class":"%s"}\n' \
      "$timestamp" "$TELEMETRY_EVENT" "$HOOK_PRESET" "$EVENT_BUDGET_MS" \
      "$STATE_BYTES_READ" "$SCAN_SCOPE" "$LOCK_OUTCOME" "$command_duration_ms" "$RESULT_CLASS" > "$tmp"
    mv "$tmp" "$TELEMETRY_FILE"
  }; then
    rm -f "$tmp" 2>/dev/null || true
  fi
}

finish() {
  status=$1
  record_hook_telemetry
  exit "$status"
}

planning_state_present() {
  for state_file in task_plan.md progress.md findings.md; do
    if [ -f "$ROOT/$state_file" ]; then
      return 0
    fi
  done
  return 1
}

emit_hook_json() {
  guard_json=""
  edit_guard_json=""
  trajectory_json=""
  planning_json=""

  if [ "$EVENT" = "pre-bash" ] && command -v python3 >/dev/null 2>&1 && [ -f "$SENSITIVE_GUARD" ]; then
    guard_json=$(python3 "$SENSITIVE_GUARD" "$ROOT" < "$PAYLOAD_FILE" 2>/dev/null || true)
  fi

  if [ "$EVENT" = "pre-edit" ] && command -v python3 >/dev/null 2>&1 && [ -f "$SENSITIVE_EDIT_GUARD" ]; then
    edit_guard_json=$(python3 "$SENSITIVE_EDIT_GUARD" --root "$ROOT" < "$PAYLOAD_FILE" 2>/dev/null || true)
  fi

  case "$EVENT" in
    session-start|user-prompt|post-bash|post-edit)
      if [ "$HOOK_PRESET" = "full" ] && command -v python3 >/dev/null 2>&1 && [ -f "$TRAJECTORY_MONITOR" ]; then
        trajectory_json=$(python3 "$TRAJECTORY_MONITOR" "$EVENT" "$ROOT" < "$PAYLOAD_FILE" 2>/dev/null || true)
      fi
      ;;
  esac

  case "$EVENT" in
    session-start|user-prompt|post-bash|stop)
      planning_event=1
      ;;
    *)
      planning_event=0
      ;;
  esac
  if [ "$planning_event" -eq 1 ] && command -v python3 >/dev/null 2>&1 && [ -f "$PLANNING_HOOK" ] && planning_state_present; then
    planning_json=$(CODEX_WORKFLOW_HOOK_TELEMETRY=1 python3 "$PLANNING_HOOK" "$EVENT" "$ROOT" < "$PAYLOAD_FILE" 2>/dev/null || true)
  elif [ "$planning_event" -eq 1 ] && ! planning_state_present; then
    # No root task document means there is no planning state to parse.  Record
    # the bounded zero-byte fact without starting the planner or JSON merger.
    STATE_BYTES_READ="0"
  fi

  if [ -z "$guard_json$edit_guard_json$trajectory_json$planning_json$STOP_SMOKE_MESSAGE" ]; then
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    if [ -n "$STOP_SMOKE_MESSAGE" ] && [ -z "$guard_json$edit_guard_json$trajectory_json$planning_json" ]; then
      printf '{"systemMessage":"Stop workflow smoke failed; see .agent-state/flags/latest-smoke.log"}\n'
    fi
    return 0
  fi

  merged_output=$(GUARD_JSON=$guard_json EDIT_GUARD_JSON=$edit_guard_json TRAJECTORY_JSON=$trajectory_json PLANNING_JSON=$planning_json STOP_SMOKE_MESSAGE=$STOP_SMOKE_MESSAGE python3 - <<'PY'
import json
import os
import sys

objects = []
state_bytes_read = "unavailable"
for raw in (
    os.environ.get("GUARD_JSON", ""),
    os.environ.get("EDIT_GUARD_JSON", ""),
    os.environ.get("TRAJECTORY_JSON", ""),
    os.environ.get("PLANNING_JSON", ""),
):
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            telemetry = obj.pop("_workflow_telemetry", None)
            if isinstance(telemetry, dict):
                candidate = telemetry.get("state_bytes_read")
                if isinstance(candidate, int) and candidate >= 0:
                    state_bytes_read = str(candidate)
            objects.append(obj)

blocks = [obj for obj in objects if obj.get("decision") == "block"]
messages = []
for obj in objects:
    msg = obj.get("systemMessage") or obj.get("reason")
    if msg:
        messages.append(str(msg))

stop_msg = os.environ.get("STOP_SMOKE_MESSAGE", "").strip()
if stop_msg:
    messages.append(stop_msg)

print(f"__CODEX_WORKFLOW_STATE_BYTES__={state_bytes_read}")

if not objects and not messages:
    sys.exit(0)

if blocks:
    out = dict(blocks[0])
    if messages:
        out["reason"] = "\n\n".join(messages)
else:
    out = {"systemMessage": "\n\n".join(messages)}

json.dump(out, sys.stdout, ensure_ascii=False)
sys.stdout.write("\n")
PY
  )

  telemetry_line=$(printf '%s\n' "$merged_output" | sed -n '1p')
  case "$telemetry_line" in
    __CODEX_WORKFLOW_STATE_BYTES__=[0-9]*)
      STATE_BYTES_READ=${telemetry_line#*=}
      ;;
  esac
  printf '%s\n' "$merged_output" | sed '1d'
}

lock_pid_alive() {
  pid=$1
  case "$pid" in
    ''|*[!0-9]*)
      return 1
      ;;
  esac
  kill -0 "$pid" 2>/dev/null
}

lock_is_stale() {
  now=$(date +%s 2>/dev/null || printf '0')
  if ! lock_epoch=$(workflow_file_mtime "$LOCK_DIR"); then
    return 1
  fi
  age=$((now - lock_epoch))
  [ "$age" -ge "$LOCK_STALE_SECONDS" ]
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_ACQUIRED=1
    LOCK_OUTCOME="acquired"
    printf '%s\n' "$$" > "$LOCK_PID_FILE"
    workflow_utc_now > "$LOCK_CREATED_FILE" 2>/dev/null || true
    return 0
  fi

  existing_pid=""
  if [ -f "$LOCK_PID_FILE" ]; then
    existing_pid=$(cat "$LOCK_PID_FILE" 2>/dev/null || true)
  fi

  if lock_pid_alive "$existing_pid"; then
    LOCK_OUTCOME="busy-skipped"
    return 1
  fi

  if lock_is_stale; then
    rm -f "$LOCK_PID_FILE" "$LOCK_CREATED_FILE" 2>/dev/null || true
    rmdir "$LOCK_DIR" 2>/dev/null || true
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      LOCK_ACQUIRED=1
      LOCK_OUTCOME="stale-recovered"
      printf '%s\n' "$$" > "$LOCK_PID_FILE"
      workflow_utc_now > "$LOCK_CREATED_FILE" 2>/dev/null || true
      return 0
    fi
  fi

  LOCK_OUTCOME="busy-skipped"
  return 1
}

record_busy_skip() {
  timestamp=$(workflow_utc_now 2>/dev/null || printf 'unknown')
  printf '%s hook-skipped-busy event=%s\n' "$timestamp" "$TELEMETRY_EVENT" > "$BUSY_SKIP_FILE" 2>/dev/null || true
}

if [ "$EVENT" = "pre-bash" ] || [ "$EVENT" = "pre-edit" ]; then
  SCAN_SCOPE="payload-guard-only"
  emit_hook_json
  finish 0
fi

if ! acquire_lock; then
  RESULT_CLASS="busy-skipped"
  record_busy_skip
  finish 0
fi

case "$EVENT" in
  session-start|user-prompt|post-bash|post-edit)
    SCAN_SCOPE="bounded-root-state"
    emit_hook_json
    finish 0
    ;;
  stop)
    SCAN_SCOPE="workflow-fingerprint"
    workflow_dirty=0
    if [ -f "$DIRTY_FLAG" ]; then
      workflow_dirty=1
    elif [ ! -f "$DIRTY_CHECKER" ]; then
      workflow_dirty=1
      RESULT_CLASS="dirty-checker-missing"
    elif sh "$DIRTY_CHECKER" --quiet >/dev/null 2>&1; then
      workflow_dirty=1
    fi

    if [ "$workflow_dirty" -eq 1 ]; then
      if [ -f "$STALE_CHECKER" ]; then
        SCAN_SCOPE="workflow-fingerprint+graphify-on-dirty"
        sh "$STALE_CHECKER" --mark --quiet --workflow-dirty-event >/dev/null 2>&1 || true
      fi
      SMOKE_RUNNER="$RUNNER"
      if [ -x "$FAST_RUNNER" ]; then
        SMOKE_RUNNER="$FAST_RUNNER"
      fi
      SCAN_SCOPE="${SCAN_SCOPE}+fast-smoke"
      if bash "$SMOKE_RUNNER" >"$LOG_FILE" 2>&1; then
        workflow_utc_now > "$LAST_FILE"
        if [ -f "$DIRTY_CHECKER" ] && sh "$DIRTY_CHECKER" --record-clean >/dev/null 2>&1; then
          rm -f "$DIRTY_FLAG" 2>/dev/null || true
        else
          printf '%s workflow smoke passed but bounded fingerprint refresh failed\n' "$(workflow_utc_now)" > "$DIRTY_FLAG"
          STOP_SMOKE_MESSAGE="Stop workflow smoke completed but bounded fingerprint refresh failed; see .agent-state/flags/latest-smoke.log"
          RESULT_CLASS="fingerprint-record-failed"
        fi
      else
        printf '%s stop smoke failed\n' "$(workflow_utc_now)" > "$DIRTY_FLAG"
        STOP_SMOKE_MESSAGE="Stop workflow smoke failed; see .agent-state/flags/latest-smoke.log"
        RESULT_CLASS="smoke-failed"
      fi
    else
      RESULT_CLASS="clean-noop"
    fi
    emit_hook_json
    finish 0
    ;;
  *)
    RESULT_CLASS="unsupported"
    finish 0
    ;;
esac
