#!/usr/bin/env python3
"""Exercise full-profile hook stdin behavior with a real PTY.

The verifier copies the installed scripts into an isolated temporary project so
it never creates lock or state files in the project passed with ``--root``.
When invoked from the source tree, ``--root starter-pack/project`` is also
supported: base helpers come from that root and full-only hook scripts fall
back to this verifier's directory.
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TIMEOUT_SECONDS = 1.5
PLANNING_NON_STOP_EVENTS = ("session-start", "user-prompt", "post-bash")
DISPATCHER_NO_PAYLOAD_EVENTS = ("session-start", "user-prompt")
FULL_ONLY_SCRIPTS = ("planning-hook.py", "hook-dispatch.sh", "planning-session-catchup.py")
REQUIRED_SCRIPTS = (
    "planning-hook.py",
    "hook-dispatch.sh",
    "portable.sh",
    "sensitive-command-guard.py",
    "sensitive_guard_policy.py",
    "hook_event_contract.py",
    "sensitive-edit-guard.py",
    "trajectory-monitor.py",
    "current_task_snapshot.py",
    "state_compat.py",
)
SOURCE_BASE_ROOT = Path(__file__).resolve().parents[5] / "project"


@dataclass
class ProcessResult:
    returncode: int | None
    timed_out: bool
    stdout: str = ""


@dataclass
class OpenTtyProcess:
    process: subprocess.Popen[str]
    master_fd: int


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for name in (
        "CODEX_PLANNING_CATCHUP",
        "CODEX_PLANNING_STRICT_STOP",
        "CODEX_SENSITIVE_GUARD_STRICT",
    ):
        env.pop(name, None)
    if extra:
        env.update(extra)
    return env


def source_for(root: Path, name: str) -> Path | None:
    installed = root / ".agents" / "scripts" / name
    if installed.is_file():
        return installed
    if root != SOURCE_BASE_ROOT.resolve():
        return None
    bundled = Path(__file__).resolve().with_name(name)
    return bundled if bundled.is_file() else None


def prepare_fixture(root: Path, destination: Path) -> Path:
    source_scripts = root / ".agents" / "scripts"
    fixture_scripts = destination / ".agents" / "scripts"
    if source_scripts.is_dir():
        shutil.copytree(source_scripts, fixture_scripts)
    else:
        fixture_scripts.mkdir(parents=True, exist_ok=True)

    for name in FULL_ONLY_SCRIPTS:
        target = fixture_scripts / name
        if target.is_file():
            continue
        source = source_for(root, name)
        if source is not None:
            shutil.copy2(source, target)

    missing = [name for name in REQUIRED_SCRIPTS if not (fixture_scripts / name).is_file()]
    if missing:
        raise RuntimeError("missing required hook script(s): " + ", ".join(missing))

    (destination / ".agent-state" / "flags").mkdir(parents=True, exist_ok=True)
    return fixture_scripts


def start_open_tty(command: list[str], cwd: Path, env: dict[str, str]) -> OpenTtyProcess:
    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=slave_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except BaseException:
        os.close(master_fd)
        os.close(slave_fd)
        raise
    os.close(slave_fd)
    return OpenTtyProcess(process=process, master_fd=master_fd)


def finish_open_tty(running: OpenTtyProcess, timeout: float) -> ProcessResult:
    try:
        stdout, _ = running.process.communicate(timeout=max(timeout, 0.05))
        return ProcessResult(returncode=running.process.returncode, timed_out=False, stdout=stdout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(running.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            running.process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(running.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            running.process.communicate()
        return ProcessResult(returncode=running.process.returncode, timed_out=True)
    finally:
        os.close(running.master_fd)


def run_closed_stdin(
    command: list[str], cwd: Path, payload: str, timeout: float, env: dict[str, str]
) -> ProcessResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            input=payload,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProcessResult(returncode=None, timed_out=True)
    return ProcessResult(returncode=completed.returncode, timed_out=False, stdout=completed.stdout)


def expect_success(failures: list[str], label: str, result: ProcessResult) -> None:
    if result.timed_out:
        failures.append(f"{label}: timed out while stdin remained open")
    elif result.returncode != 0:
        failures.append(f"{label}: exited with status {result.returncode}")


def json_object(text: str) -> dict[str, object] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def expect_json_or_empty(failures: list[str], label: str, result: ProcessResult) -> None:
    if result.timed_out or not result.stdout.strip():
        return
    if json_object(result.stdout) is None:
        failures.append(f"{label}: stdout was not valid hook JSON")


def verify_open_stdin(
    failures: list[str], scripts: Path, fixture: Path, timeout: float, env: dict[str, str]
) -> None:
    planning_hook = [sys.executable, str(scripts / "planning-hook.py")]
    for event in PLANNING_NON_STOP_EVENTS:
        result = finish_open_tty(
            start_open_tty([*planning_hook, event, str(fixture)], fixture, env),
            timeout,
        )
        expect_success(failures, f"planning hook {event}", result)
        expect_json_or_empty(failures, f"planning hook {event}", result)

    dispatcher = scripts / "hook-dispatch.sh"
    started = [
        (event, start_open_tty(["sh", str(dispatcher), event], fixture, env))
        for event in DISPATCHER_NO_PAYLOAD_EVENTS
    ]
    deadline = time.monotonic() + timeout
    for event, running in started:
        result = finish_open_tty(running, deadline - time.monotonic())
        expect_success(failures, f"dispatcher {event}", result)
        expect_json_or_empty(failures, f"dispatcher {event}", result)


def verify_tool_payloads(
    failures: list[str], scripts: Path, fixture: Path, timeout: float, env: dict[str, str]
) -> None:
    dispatcher = scripts / "hook-dispatch.sh"
    payloads = (
        (
            "post-bash",
            {
                "session_id": "protocol-session",
                "turn_id": "protocol-turn",
                "cwd": str(fixture),
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_use_id": "bash-protocol",
                "tool_input": {"command": "pytest -q"},
                "tool_response": {"exit_code": 0, "output": "pass"},
            },
        ),
        (
            "pre-edit",
            {
                "session_id": "protocol-session",
                "turn_id": "protocol-turn",
                "cwd": str(fixture),
                "hook_event_name": "PreToolUse",
                "tool_name": "apply_patch",
                "tool_use_id": "edit-pre-protocol",
                "tool_input": {
                    "command": "*** Begin Patch\n*** Update File: .git/HEAD\n@@\n-old\n+new\n*** End Patch\n"
                },
            },
        ),
        (
            "post-edit",
            {
                "session_id": "protocol-session",
                "turn_id": "protocol-turn",
                "cwd": str(fixture),
                "hook_event_name": "PostToolUse",
                "tool_name": "apply_patch",
                "tool_use_id": "edit-post-protocol",
                "tool_input": {
                    "command": "*** Begin Patch\n*** Update File: src/app.py\n@@\n-old\n+new\n*** End Patch\n"
                },
                "tool_response": {"status": "success"},
            },
        ),
    )
    for event, payload in payloads:
        result = run_closed_stdin(
            ["sh", str(dispatcher), event],
            fixture,
            json.dumps(payload),
            timeout,
            env,
        )
        expect_success(failures, f"dispatcher {event} payload", result)
        expect_json_or_empty(failures, f"dispatcher {event} payload", result)
        if event == "pre-edit":
            response = json_object(result.stdout)
            if response is None or response.get("decision") != "block" or response.get("hardline") is not True:
                failures.append("dispatcher pre-edit payload: hardline edit block was not preserved")


def verify_stop_payloads(
    failures: list[str], scripts: Path, fixture: Path, timeout: float, env: dict[str, str]
) -> None:
    command = [sys.executable, str(scripts / "planning-hook.py"), "stop", str(fixture)]
    for label, payload in (
        ("empty", ""),
        ("malformed", "{"),
        ("valid", '{"stop_hook_active": true}'),
    ):
        result = run_closed_stdin(command, fixture, payload, timeout, env)
        expect_success(
            failures,
            f"stop payload {label}",
            result,
        )
        expect_json_or_empty(failures, f"stop payload {label}", result)


def verify_lock_behavior(
    failures: list[str], scripts: Path, fixture: Path, timeout: float, env: dict[str, str]
) -> None:
    flags = fixture / ".agent-state" / "flags"
    lock_dir = flags / "workflow.lock"
    lock_dir.mkdir()
    (lock_dir / "pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
    dispatcher = scripts / "hook-dispatch.sh"

    busy_result = run_closed_stdin(["sh", str(dispatcher), "user-prompt"], fixture, "", timeout, env)
    expect_success(failures, "busy dispatcher user-prompt", busy_result)
    expect_json_or_empty(failures, "busy dispatcher user-prompt", busy_result)
    busy_marker = flags / "hook-skipped-busy.last"
    if not busy_marker.is_file() or "hook-skipped-busy" not in busy_marker.read_text(encoding="utf-8"):
        failures.append("busy dispatcher user-prompt: missing report-only hook-skipped-busy marker")

    guard_result = run_closed_stdin(
        ["sh", str(dispatcher), "pre-bash"],
        fixture,
        '{"command": "rm -rf /"}',
        timeout,
        env,
    )
    expect_success(failures, "pre-bash sensitive guard with busy planning lock", guard_result)
    guard_payload = json_object(guard_result.stdout)
    if guard_result.returncode != 0 or guard_payload is None:
        failures.append("pre-bash sensitive guard with busy planning lock: missing JSON guard response")
    else:
        if guard_payload.get("decision") != "block" or guard_payload.get("hardline") is not True:
            failures.append("pre-bash sensitive guard with busy planning lock: hardline block was not preserved")

    shutil.rmtree(lock_dir)
    lock_dir.mkdir()
    (lock_dir / "pid").write_text("999999\n", encoding="utf-8")
    os.utime(lock_dir, (1, 1))
    stale_env = clean_env({"CODEX_WORKFLOW_LOCK_STALE_SECONDS": "1"})
    stale_result = run_closed_stdin(
        ["sh", str(dispatcher), "session-start"], fixture, "", timeout, stale_env
    )
    expect_success(failures, "stale lock dispatcher session-start", stale_result)
    if lock_dir.exists():
        failures.append("stale lock dispatcher session-start: stale lock was not recovered")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify full-profile hook TTY/stdin protocol behavior.")
    parser.add_argument("--root", required=True, help="Applied project root, or starter-pack/project in source mode.")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()
    if not 0 < args.timeout_seconds <= 2:
        parser.error("--timeout-seconds must be greater than 0 and no more than 2")
    return args


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="planning-hook-protocol-") as temp_dir:
            fixture = Path(temp_dir) / "project"
            scripts = prepare_fixture(root, fixture)
            env = clean_env()
            verify_open_stdin(failures, scripts, fixture, args.timeout_seconds, env)
            verify_tool_payloads(failures, scripts, fixture, args.timeout_seconds, env)
            verify_stop_payloads(failures, scripts, fixture, args.timeout_seconds, env)
            verify_lock_behavior(failures, scripts, fixture, args.timeout_seconds, env)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        failures.append(f"setup: {error}")

    if failures:
        for failure in failures:
            print(f"fail: planning hook protocol: {failure}", file=sys.stderr)
        return 1
    print("pass: planning hook protocol PTY, tool payload, lock, and pre-tool guard checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
