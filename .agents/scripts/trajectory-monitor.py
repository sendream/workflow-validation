#!/usr/bin/env python3
"""Bounded, warn-only trajectory signals for full-profile tool hooks."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import hook_event_contract as hook_contract


STATE_VERSION = 1
FAILURE_THRESHOLD = 3
EDIT_THRESHOLD = 5
COOLING_EVENTS = 5
MAX_WARNINGS_PER_SIGNAL = 2
STATE_RELATIVE = Path(".agent-state/flags/trajectory-monitor.json")
BUSY_SKIP_RELATIVE = Path(".agent-state/flags/hook-skipped-busy.last")


def empty_signal() -> dict[str, Any]:
    return {"subject_digest": "", "cwd_digest": "", "count": 0, "cooldown_until": 0, "warnings": 0}


def fresh_state(root: Path, *, epoch: int = 0) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "epoch": epoch,
        "event_seq": 0,
        "session_digest": "",
        "turn_digest": "",
        "busy_skip_digest": busy_skip_digest(root),
        "fallback_verifier_seen": False,
        "failure": empty_signal(),
        "edit": empty_signal(),
    }


def busy_skip_digest(root: Path) -> str:
    path = root / BUSY_SKIP_RELATIVE
    try:
        return hook_contract.stable_digest(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def valid_signal(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        isinstance(value.get("subject_digest"), str)
        and isinstance(value.get("cwd_digest"), str)
        and all(
            isinstance(value.get(key), int)
            and not isinstance(value.get(key), bool)
            and value[key] >= 0
            for key in ("count", "cooldown_until", "warnings")
        )
    )


def valid_state(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("version") == STATE_VERSION
        and all(
            isinstance(value.get(key), int)
            and not isinstance(value.get(key), bool)
            and value[key] >= 0
            for key in ("epoch", "event_seq")
        )
        and all(isinstance(value.get(key), str) for key in ("session_digest", "turn_digest", "busy_skip_digest"))
        and isinstance(value.get("fallback_verifier_seen"), bool)
        and valid_signal(value.get("failure"))
        and valid_signal(value.get("edit"))
    )


def load_state(root: Path) -> dict[str, Any]:
    path = root / STATE_RELATIVE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fresh_state(root)
    if not valid_state(value):
        return fresh_state(root)
    return value


def atomic_write_state(root: Path, state: dict[str, Any]) -> None:
    path = root / STATE_RELATIVE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".trajectory-monitor.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        try:
            if "temporary" in locals():
                os.unlink(temporary)
        except OSError:
            pass


def reset_windows(state: dict[str, Any]) -> None:
    state["event_seq"] = 0
    state["fallback_verifier_seen"] = False
    state["failure"] = empty_signal()
    state["edit"] = empty_signal()


def prepare_state(root: Path, state: dict[str, Any], payload: dict[str, Any]) -> None:
    marker = busy_skip_digest(root)
    if marker != state.get("busy_skip_digest", ""):
        reset_windows(state)
        state["busy_skip_digest"] = marker

    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id:
        session_digest = hook_contract.stable_digest(session_id)
        previous = state.get("session_digest", "")
        if previous and previous != session_digest:
            reset_windows(state)
        state["session_digest"] = session_digest

    turn_id = payload.get("turn_id")
    if isinstance(turn_id, str) and turn_id:
        turn_digest = hook_contract.stable_digest(turn_id)
        previous_turn = state.get("turn_digest", "")
        if previous_turn and previous_turn != turn_digest:
            reset_windows(state)
        state["turn_digest"] = turn_digest


def reset_signal(signal: dict[str, Any]) -> None:
    signal["subject_digest"] = ""
    signal["cwd_digest"] = ""
    signal["count"] = 0


def warning_ready(signal: dict[str, Any], event_seq: int) -> bool:
    return int(signal.get("warnings", 0)) < MAX_WARNINGS_PER_SIGNAL and event_seq >= int(
        signal.get("cooldown_until", 0)
    )


def record_warning(signal: dict[str, Any], event_seq: int) -> None:
    signal["warnings"] = int(signal.get("warnings", 0)) + 1
    signal["cooldown_until"] = event_seq + COOLING_EVENTS


def handle_post_bash(root: Path, state: dict[str, Any], payload: dict[str, Any]) -> str:
    command = hook_contract.normalized_command(hook_contract.payload_command(payload))
    exit_code = hook_contract.response_exit_code(payload)
    if payload.get("tool_name") != "Bash" or not command or exit_code is None:
        reset_windows(state)
        return ""

    state["event_seq"] = int(state.get("event_seq", 0)) + 1
    event_seq = state["event_seq"]
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else str(root)
    cwd_digest = hook_contract.stable_digest(str(cwd))
    command_digest = hook_contract.stable_digest(command)
    failure = state["failure"]

    message = ""
    if exit_code != 0:
        if failure.get("subject_digest") == command_digest and failure.get("cwd_digest") == cwd_digest:
            failure["count"] = int(failure.get("count", 0)) + 1
        else:
            reset_signal(failure)
            failure["subject_digest"] = command_digest
            failure["cwd_digest"] = cwd_digest
            failure["count"] = 1
        if int(failure["count"]) >= FAILURE_THRESHOLD and warning_ready(failure, event_seq):
            record_warning(failure, event_seq)
            message = (
                "[trajectory-monitor] The same command in the same cwd has failed at least 3 consecutive times. "
                "Record the failed path and new evidence, then change strategy before retrying."
            )
    else:
        reset_signal(failure)
        declared = hook_contract.declared_verifier_prefixes(root)
        is_verifier, source = hook_contract.recognized_verifier(command, declared)
        if is_verifier:
            if source == "fallback":
                state["fallback_verifier_seen"] = True
            reset_signal(state["edit"])
    return message


def edit_signal_active(root: Path, state: dict[str, Any]) -> bool:
    return bool(hook_contract.declared_verifier_prefixes(root)) or bool(state.get("fallback_verifier_seen"))


def handle_post_edit(root: Path, state: dict[str, Any], payload: dict[str, Any]) -> str:
    if not hook_contract.is_apply_patch_payload(payload):
        reset_signal(state["edit"])
        return ""
    succeeded = hook_contract.response_succeeded(payload)
    envelope = hook_contract.parse_apply_patch(hook_contract.payload_command(payload))
    if succeeded is not True or len(envelope.targets) != 1:
        reset_signal(state["edit"])
        return ""

    state["event_seq"] = int(state.get("event_seq", 0)) + 1
    if not edit_signal_active(root, state):
        reset_signal(state["edit"])
        return ""

    event_seq = state["event_seq"]
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else str(root)
    cwd_digest = hook_contract.stable_digest(str(cwd))
    path_digest = hook_contract.stable_digest(envelope.targets[0])
    edit = state["edit"]
    if edit.get("subject_digest") == path_digest and edit.get("cwd_digest") == cwd_digest:
        edit["count"] = int(edit.get("count", 0)) + 1
    else:
        reset_signal(edit)
        edit["subject_digest"] = path_digest
        edit["cwd_digest"] = cwd_digest
        edit["count"] = 1

    if int(edit["count"]) >= EDIT_THRESHOLD and warning_ready(edit, event_seq):
        record_warning(edit, event_seq)
        return (
            "[trajectory-monitor] The same file has been edited at least 5 times in this turn without a successful "
            "recognized verification command. Run the declared/fallback verifier or update the plan before another edit."
        )
    return ""


def emit_warning(message: str) -> None:
    if not message:
        return
    json.dump({"systemMessage": message}, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 0
    event, root_value = argv
    root = Path(root_value).resolve()

    if event == "session-start":
        atomic_write_state(root, fresh_state(root))
        return 0

    state = load_state(root)
    if event == "user-prompt":
        epoch = int(state.get("epoch", 0)) + 1
        state = fresh_state(root, epoch=epoch)
        atomic_write_state(root, state)
        return 0

    if event not in {"post-bash", "post-edit"}:
        return 0

    payload = hook_contract.load_payload(sys.stdin.read())
    prepare_state(root, state, payload)
    if event == "post-bash":
        message = handle_post_bash(root, state, payload)
    else:
        message = handle_post_edit(root, state, payload)
    atomic_write_state(root, state)
    emit_warning(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
