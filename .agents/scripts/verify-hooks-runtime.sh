#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)
FORMAT=text
FAIL_ON_BROKEN=0
FAIL_ON_DEGRADED=0
FAIL_ON_DUPLICATE=0

usage() {
  cat <<'EOF'
Usage:
  verify-hooks-runtime.sh [--format text|json] [project-root] [strict options]

Strict options:
  --fail-on-broken                   Exit 2 when hooks runtime is broken.
  --fail-on-degraded                 Exit 3 when hooks runtime is not healthy.
  --fail-on-duplicate-command-event  Exit 4 when one event has overlapping command hooks.

Requires python3 >= 3.11 (tomllib); exits 5 with a clear error otherwise.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --format)
      FORMAT=${2:-text}
      shift 2
      ;;
    --fail-on-broken)
      FAIL_ON_BROKEN=1
      shift
      ;;
    --fail-on-degraded)
      FAIL_ON_DEGRADED=1
      shift
      ;;
    --fail-on-duplicate-command-event)
      FAIL_ON_DUPLICATE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      printf 'verify-hooks-runtime: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      ROOT=$1
      shift
      ;;
  esac
done

HOOKS_FILE="$ROOT/.codex/hooks.json"
STATE_DIR="$ROOT/.agent-state/flags"
LEGACY_STATE_DIR="$ROOT/.agents/state"
CONFIG_HOME=${CODEX_HOME:-$HOME/.codex}

# The runtime check below imports tomllib (Python 3.11+). Gate the interpreter
# explicitly so old environments get a contract-level error instead of a
# traceback and partial output.
if ! command -v python3 >/dev/null 2>&1; then
  printf 'verify-hooks-runtime: python3 not found; Python >= 3.11 is required for hooks runtime checks (tomllib)\n' >&2
  exit 5
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  found_python=$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || printf 'unknown')
  printf 'verify-hooks-runtime: Python >= 3.11 is required for hooks runtime checks (tomllib); found python3 %s\n' "$found_python" >&2
  exit 5
fi

python3 - "$ROOT" "$HOOKS_FILE" "$STATE_DIR" "$LEGACY_STATE_DIR" "$CONFIG_HOME/config.toml" "$FORMAT" "$FAIL_ON_BROKEN" "$FAIL_ON_DEGRADED" "$FAIL_ON_DUPLICATE" "$SCRIPT_DIR" <<'PY'
from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path

root = Path(sys.argv[1])
hooks_file = Path(sys.argv[2])
state_dir = Path(sys.argv[3])
legacy_state_dir = Path(sys.argv[4])
config_file = Path(sys.argv[5])
output_format = sys.argv[6]
fail_on_broken = sys.argv[7] == "1"
fail_on_degraded = sys.argv[8] == "1"
fail_on_duplicate = sys.argv[9] == "1"
script_dir = Path(sys.argv[10])
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from state_compat import lookup_path

known_events = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def feature_flag_status() -> str:
    text = read_text(config_file)
    if "codex_hooks" not in text:
        return "unknown"
    return "enabled" if "codex_hooks = true" in text else "disabled-or-unknown"


def wsl_to_windows(path: Path) -> list[str]:
    text = str(path)
    parts = text.split("/")
    if len(parts) >= 4 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        win = f"{drive}:\\{rest}" if rest else f"{drive}:\\"
        return [win, f"\\\\?\\{win}"]
    return []


def project_path_candidates(path: Path) -> set[str]:
    candidates = {str(path), str(path.resolve())}
    candidates.update(wsl_to_windows(path))
    return candidates


def project_trust_status() -> str:
    if not config_file.exists():
        return "unknown-no-config"

    try:
        data = tomllib.loads(read_text(config_file))
    except Exception:
        return "unknown-config-unreadable"

    projects = data.get("projects")
    if not isinstance(projects, dict):
        return "unknown-no-projects"

    candidates = project_path_candidates(root)
    for project_path, project_data in projects.items():
        if project_path not in candidates:
            continue
        if isinstance(project_data, dict):
            trust_level = str(project_data.get("trust_level", "unknown"))
            return trust_level
        return "unknown-invalid-project-entry"

    return "unknown-not-listed"


def writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


hooks_data: dict[str, object] = {}
hooks_valid = False
if hooks_file.exists():
    try:
        parsed = json.loads(read_text(hooks_file))
        hooks_data = parsed if isinstance(parsed, dict) else {}
        hooks_valid = isinstance(parsed, dict)
    except json.JSONDecodeError:
        hooks_valid = False

hooks = hooks_data.get("hooks") if isinstance(hooks_data.get("hooks"), dict) else {}
unknown_hook_types = sorted(set(hooks) - known_events) if isinstance(hooks, dict) else []
command_counts: dict[str, int] = {}
matcher_counts: dict[str, int] = {}
concurrent_event_names: set[str] = set()
if isinstance(hooks, dict):
    for event, groups in hooks.items():
        count = 0
        event_matcher_counts: dict[str, int] = {}
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                matcher = str(group.get("matcher") or "*")
                handlers = group.get("hooks")
                if not isinstance(handlers, list):
                    continue
                group_count = sum(1 for item in handlers if isinstance(item, dict) and item.get("type") == "command")
                count += group_count
                event_matcher_counts[matcher] = event_matcher_counts.get(matcher, 0) + group_count
        command_counts[str(event)] = count
        for matcher, matcher_count in event_matcher_counts.items():
            matcher_counts[f"{event}:{matcher}"] = matcher_count
            if matcher_count > 1:
                concurrent_event_names.add(str(event))
        if event_matcher_counts.get("*", 0) and len(event_matcher_counts) > 1:
            concurrent_event_names.add(str(event))

concurrent_events = sorted(concurrent_event_names)
current_flag_names = {path.name for path in state_dir.glob("*.enabled")} if state_dir.exists() else set()
legacy_flag_names = {path.name for path in legacy_state_dir.glob("*.enabled")} if legacy_state_dir.exists() else set()
strict_flags: list[str] = []
strict_flag_origins: dict[str, str] = {}
for name in sorted(current_flag_names | legacy_flag_names):
    lookup = lookup_path(
        state_dir / name,
        legacy_state_dir / name,
        deprecated_since="2026-07-22",
        remove_after="2026-12-31",
    )
    if lookup.origin == "missing":
        continue
    strict_flags.append(name)
    strict_flag_origins[name] = lookup.origin

checks = {
    "codex_hooks_feature_flag": feature_flag_status(),
    "project_hooks_file": hooks_file.exists(),
    "hooks_json_valid": hooks_valid,
    "project_trust": project_trust_status(),
    "hook_root": "git-root" if (root / ".git").exists() else "workspace-root-or-non-git",
    "python3_available": True,
    "state_dir": str(state_dir.relative_to(root)) if state_dir.is_relative_to(root) else str(state_dir),
    "state_dir_writable": writable(state_dir),
    "legacy_state_dir_present": legacy_state_dir.exists(),
    "strict_flags_enabled": strict_flags,
    "strict_flag_origins": strict_flag_origins,
    "unknown_hook_types": unknown_hook_types,
    "command_hooks_per_event": command_counts,
    "command_hooks_per_event_matcher": matcher_counts,
    "concurrent_command_hook_events": concurrent_events,
}

status = "healthy"
if not checks["state_dir_writable"] or not hooks_valid:
    status = "broken"
elif checks["codex_hooks_feature_flag"] != "enabled" or checks["project_trust"] != "trusted":
    status = "degraded"

payload = {
    "status": status,
    "checks": checks,
    "notes": [
        "Matching hooks from multiple files may all run; duplicate command hooks with the same matcher, or an unmatched hook plus a matched hook, can start concurrently.",
        "Project trust and codex_hooks feature flag may need manual confirmation with codex /status and config.toml.",
    ],
}

if output_format == "json":
    print(json.dumps(payload, ensure_ascii=False, indent=2))
else:
    print(f"HOOKS RUNTIME STATUS: {status}")
    for key, value in checks.items():
        print(f"- {key}: {value}")

exit_code = 0
if fail_on_broken and status == "broken":
    exit_code = max(exit_code, 2)
if fail_on_degraded and status != "healthy":
    exit_code = max(exit_code, 3)
if fail_on_duplicate and concurrent_events:
    exit_code = max(exit_code, 4)

raise SystemExit(exit_code)
PY
