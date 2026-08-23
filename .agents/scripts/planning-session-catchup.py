#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from state_compat import lookup_path


PLANNING_FILES = ("task_plan.md", "progress.md", "findings.md")
MAX_SESSIONS = 80
MAX_ITEMS = 12
MIN_SESSION_BYTES = 5000
STATE_COMPAT_DEPRECATED_SINCE = "2026-07-22"
STATE_COMPAT_REMOVE_AFTER = "2026-12-31"


def json_loads(line: str) -> dict[str, Any] | None:
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def normalize(path: str) -> str:
    try:
        return str(Path(os.path.expanduser(path)).resolve())
    except (OSError, ValueError):
        return os.path.abspath(os.path.expanduser(path))


def enabled(root: Path) -> bool:
    # Explicit opt-in only. This avoids reading ~/.codex/sessions in projects
    # that did not choose session recovery.
    enabled_file = root / ".agent-state" / "flags" / "planning-session-catchup.enabled"
    legacy_file = root / ".agents" / "state" / "planning-session-catchup.enabled"
    lookup = lookup_path(
        enabled_file,
        legacy_file,
        deprecated_since=STATE_COMPAT_DEPRECATED_SINCE,
        remove_after=STATE_COMPAT_REMOVE_AFTER,
    )
    return lookup.origin != "missing" or os.getenv("CODEX_PLANNING_CATCHUP") == "1"


def read_meta(session: Path) -> dict[str, Any] | None:
    try:
        with session.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                data = json_loads(line)
                if not data or data.get("type") != "session_meta":
                    continue
                payload = data.get("payload")
                return payload if isinstance(payload, dict) else None
    except OSError:
        return None
    return None


def is_project_session(session: Path, root_cmp: str) -> bool:
    try:
        if session.stat().st_size < MIN_SESSION_BYTES:
            return False
    except OSError:
        return False

    meta = read_meta(session)
    if not meta:
        return False
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return False
    cwd = meta.get("cwd")
    return isinstance(cwd, str) and normalize(cwd) == root_cmp


def candidate_sessions(root: Path) -> list[Path]:
    sessions_dir = Path(os.path.expanduser(os.getenv("CODEX_SESSIONS_DIR", "~/.codex/sessions")))
    if not sessions_dir.exists():
        return []
    root_cmp = normalize(str(root))
    sessions = sorted(
        sessions_dir.rglob("rollout-*.jsonl"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    return [session for session in sessions[:MAX_SESSIONS] if is_project_session(session, root_cmp)]


def planning_file_from_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    for name in PLANNING_FILES:
        if value.endswith(name):
            return name
    return None


def planning_update_from_event(payload: dict[str, Any]) -> str | None:
    if payload.get("type") != "patch_apply_end" or payload.get("success") is not True:
        return None
    changes = payload.get("changes")
    if not isinstance(changes, dict):
        return None
    for path in changes:
        match = planning_file_from_path(path)
        if match:
            return match
    return None


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts)


def summarize_tool(payload: dict[str, Any]) -> str:
    name = payload.get("name")
    raw = payload.get("arguments", payload.get("input", ""))
    args: dict[str, Any] = {}
    if isinstance(raw, str):
        decoded = json_loads(raw)
        if decoded:
            args = decoded
    elif isinstance(raw, dict):
        args = raw
    if name == "exec_command":
        cmd = args.get("cmd", "")
        return f"exec_command: {str(cmd)[:100]}"
    return str(name or "tool")


def parse_session(session: Path) -> tuple[int, str | None, list[str]]:
    last_update_line = -1
    last_update_file: str | None = None
    items: list[tuple[int, str]] = []

    try:
        with session.open("r", encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh):
                data = json_loads(line)
                if not data:
                    continue
                msg_type = data.get("type")

                if msg_type == "event_msg":
                    payload = data.get("payload")
                    if isinstance(payload, dict):
                        updated = planning_update_from_event(payload)
                        if updated:
                            last_update_line = line_no
                            last_update_file = updated
                    continue

                if line_no <= last_update_line:
                    continue

                if msg_type == "response_item":
                    payload = data.get("payload")
                    if not isinstance(payload, dict):
                        continue
                    payload_type = payload.get("type")
                    if payload_type == "message":
                        role = payload.get("role")
                        content = text_from_content(payload.get("content")).strip()
                        if role in ("user", "assistant") and len(content) > 20:
                            items.append((line_no, f"{role}: {content[:220]}"))
                    elif payload_type in ("function_call", "custom_tool_call"):
                        items.append((line_no, f"tool: {summarize_tool(payload)}"))
    except OSError:
        return -1, None, []

    if last_update_line < 0:
        return -1, None, []
    unsynced = [item for line_no, item in items if line_no > last_update_line]
    return last_update_line, last_update_file, unsynced[-MAX_ITEMS:]


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not enabled(root):
        return 0
    if not any((root / name).exists() for name in PLANNING_FILES):
        return 0

    for session in candidate_sessions(root):
        line_no, filename, items = parse_session(session)
        if line_no < 0 or not items:
            continue
        print("[planning-with-files] SESSION CATCHUP")
        print(f"session: {session.name}")
        print(f"last planning update: {filename} at line {line_no}")
        print("unsynced context after last planning update:")
        for item in items:
            print(f"- {item}")
        print("recommended: read task_plan.md, progress.md, findings.md, then update planning files if needed.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
