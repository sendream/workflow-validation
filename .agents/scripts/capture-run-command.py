#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_manifest_contract import (
    candidate_file_sha256,
    validate_candidate_result_artifact,
    validate_workflow_attribution,
)


RUN_ID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
SHELL_PROGRAMS = {"sh", "bash", "dash", "zsh", "ksh", "pwsh", "powershell"}
INLINE_EVAL_FLAGS = {
    "node": {"-e", "--eval", "-p", "--print"},
    "perl": {"-e"},
    "php": {"-r", "-B", "-R", "-E"},
    "ruby": {"-e"},
}
PYTHON_PROGRAM_RE = re.compile(r"^python(?:\d+(?:\.\d+)*)?(?:\.exe)?$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_run_id(value: str) -> bool:
    return bool(value) and all(char in RUN_ID_CHARS for char in value) and ".." not in value


def default_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def brief(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "empty"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "\n...[truncated]"


def command_error(argv: list[str]) -> str | None:
    if not argv:
        return "empty-command"
    executable = Path(argv[0]).name.lower()
    if executable in SHELL_PROGRAMS and any(arg in {"-c", "/c", "-Command", "-EncodedCommand"} for arg in argv[1:]):
        return "shell-eval-not-allowed"
    if executable == "env":
        return "env-assignment-not-allowed"
    if inline_eval_reentry(argv):
        return "inline-eval-not-allowed"
    return None


def inline_eval_reentry(argv: list[str]) -> bool:
    for index, token in enumerate(argv):
        program = Path(token).name.lower()
        flags = {"-c"} if PYTHON_PROGRAM_RE.fullmatch(program) else INLINE_EVAL_FLAGS.get(program, set())
        if flags and any(arg in flags for arg in argv[index + 1 :]):
            return True
    return False


def first_env_command(args: list[str]) -> str:
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            break
        if re_full_env_assignment(token):
            index += 1
            continue
        if token in {"-i", "-0"}:
            index += 1
            continue
        if token in {"-u", "-C", "-S"}:
            if token == "-S" and index + 1 < len(args):
                try:
                    split_args = shlex.split(args[index + 1], posix=True)
                except ValueError:
                    return args[index + 1]
                return first_env_command(split_args)
            index += 2
            continue
        if token.startswith("--ignore-environment") or token.startswith("--null"):
            index += 1
            continue
        if token.startswith("--unset=") or token.startswith("--chdir=") or token.startswith("--split-string="):
            if token.startswith("--split-string="):
                try:
                    split_args = shlex.split(token.split("=", 1)[1], posix=True)
                except ValueError:
                    return token.split("=", 1)[1]
                return first_env_command(split_args)
            index += 1
            continue
        if token.startswith("-"):
            return token
        break
    return args[index] if index < len(args) else ""


def re_full_env_assignment(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", value))


def write_manifest(
    root: Path,
    run_dir: Path,
    run_id: str,
    argv: list[str],
    exit_code: int,
    status: str,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    stdout_path: Path,
    stderr_path: Path,
    summary: str,
    linked_acceptance_ids: list[str],
    linked_scenario_ids: list[str],
    blocked_reason: str = "not-needed",
    workflow_attribution: dict[str, str] | None = None,
) -> Path:
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": completed_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "tool_runtime_ms": duration_ms,
        "command": shlex.join(argv),
        "command_argv": argv,
        "exit_code": exit_code,
        "status": status,
        "summary": summary,
        "stdout_path": str(stdout_path.relative_to(run_dir)),
        "stderr_path": str(stderr_path.relative_to(run_dir)),
        "stdout_summary": brief(stdout_path.read_text(encoding="utf-8", errors="replace")),
        "stderr_summary": brief(stderr_path.read_text(encoding="utf-8", errors="replace")),
        "sha256": {
            "stdout": sha256_file(stdout_path),
            "stderr": sha256_file(stderr_path),
        },
        "linked_acceptance_ids": linked_acceptance_ids,
        "linked_scenario_ids": linked_scenario_ids,
        "artifacts": [],
        "blocked_reason": blocked_reason,
        "redaction_status": "unknown",
        "token_usage": {"status": "unavailable"},
        "estimated_cost": {"status": "unavailable"},
        "external_lookup_ledger": [],
    }
    if workflow_attribution is not None:
        manifest["workflow_attribution"] = workflow_attribution
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a local validation command as .agent-state/runs/<run_id>/manifest.json evidence."
    )
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--run-id", default="", help="Run id. Defaults to run-<UTC timestamp>.")
    parser.add_argument("--cwd", default="", help="Command working directory, relative to root by default.")
    parser.add_argument("--summary", default="", help="Human summary for manifest.summary.")
    parser.add_argument("--acceptance-id", action="append", default=[], help="Acceptance id linked to this run. May repeat.")
    parser.add_argument("--scenario-id", action="append", default=[], help="Scenario id linked to this run. May repeat.")
    parser.add_argument("--timeout", type=float, default=None, help="Optional timeout in seconds.")
    parser.add_argument("--component-id", default="", help="Optional workflow mechanism attribution.")
    parser.add_argument("--candidate-id", default="", help="Optional workflow change candidate id.")
    parser.add_argument("--candidate-ref", default="", help="Optional project-relative candidate artifact whose digest binds evolution evidence.")
    parser.add_argument("--candidate-result-ref", default="", help="Project-relative command-produced candidate evaluation JSON under this run directory.")
    parser.add_argument("--attribution-phase", default="", help="Optional baseline/validation/pilot/rollback-check phase.")
    parser.add_argument("--task-epoch", default="", help="Optional current/migration/legacy attribution epoch.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command argv after --.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    run_id = args.run_id or default_run_id()
    if not safe_run_id(run_id):
        print(f"capture-run-command: unsafe run id: {run_id}", file=sys.stderr)
        return 2
    run_dir = root / ".agent-state" / "runs" / run_id
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    error = command_error(command)
    if error:
        print(f"capture-run-command: rejected command: {error}", file=sys.stderr)
        return 2

    attribution_values = (args.component_id, args.candidate_id, args.attribution_phase, args.task_epoch)
    workflow_attribution: dict[str, str] | None = None
    if any(attribution_values):
        if not all(attribution_values):
            print(
                "capture-run-command: workflow attribution fields are all-or-none: "
                "--component-id --candidate-id --attribution-phase --task-epoch",
                file=sys.stderr,
            )
            return 2
        workflow_attribution = {
            "candidate_id": args.candidate_id,
            "component_id": args.component_id,
            "phase": args.attribution_phase,
            "task_epoch": args.task_epoch,
        }
        if args.candidate_ref:
            candidate_sha256, candidate_error = candidate_file_sha256(root, args.candidate_ref)
            if candidate_error or candidate_sha256 is None:
                print(f"capture-run-command: {candidate_error or 'invalid candidate_ref'}", file=sys.stderr)
                return 2
            workflow_attribution["candidate_sha256"] = candidate_sha256
            workflow_attribution["candidate_ref"] = args.candidate_ref
        if args.attribution_phase in {"validation", "pilot", "rollback-check"}:
            if not args.candidate_ref:
                print(
                    "capture-run-command: validation/pilot/rollback-check attribution requires --candidate-ref",
                    file=sys.stderr,
                )
                return 2
            if not args.candidate_result_ref:
                print(
                    "capture-run-command: validation/pilot/rollback-check attribution requires --candidate-result-ref",
                    file=sys.stderr,
                )
                return 2
            result_path = root / args.candidate_result_ref
            try:
                result_path.resolve().relative_to(run_dir.resolve())
            except ValueError:
                print("capture-run-command: candidate-result-ref must stay under this run directory", file=sys.stderr)
                return 2
            if args.candidate_ref not in command or args.candidate_result_ref not in command:
                print(
                    "capture-run-command: attributed validation command must receive candidate_ref and candidate_result_ref as exact argv tokens",
                    file=sys.stderr,
                )
                return 2
        attribution_errors = validate_workflow_attribution(workflow_attribution)
        if attribution_errors:
            print("capture-run-command: " + "; ".join(attribution_errors), file=sys.stderr)
            return 2
    elif args.candidate_ref or args.candidate_result_ref:
        print("capture-run-command: candidate refs require complete workflow attribution", file=sys.stderr)
        return 2

    cwd = Path(args.cwd) if args.cwd else root
    if not cwd.is_absolute():
        cwd = root / cwd
    if (run_dir / "manifest.json").exists():
        print(f"capture-run-command: run manifest already exists: {run_dir / 'manifest.json'}", file=sys.stderr)
        return 2
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = outputs_dir / "stdout.txt"
    stderr_path = outputs_dir / "stderr.txt"

    started_at = utc_now()
    started = time.monotonic()
    status = "fail"
    exit_code = 127
    blocked_reason = "not-needed"
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
        )
        exit_code = result.returncode
        stdout_path.write_text(result.stdout, encoding="utf-8", errors="replace")
        stderr_path.write_text(result.stderr, encoding="utf-8", errors="replace")
        status = "pass" if exit_code == 0 else "fail"
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout_path.write_text(exc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text((exc.stderr or "") + f"\ncommand timed out after {args.timeout} seconds\n", encoding="utf-8", errors="replace")
        status = "blocked"
        blocked_reason = "timeout"
    except FileNotFoundError as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
        status = "fail"
        blocked_reason = "command-not-found"
    if workflow_attribution is not None and args.attribution_phase in {"validation", "pilot", "rollback-check"}:
        result_sha256, result_error = candidate_file_sha256(root, args.candidate_result_ref)
        candidate_result_errors: list[str] = []
        if result_error or result_sha256 is None:
            candidate_result_errors.append(result_error or "candidate result digest unavailable")
        else:
            workflow_attribution["candidate_result_ref"] = args.candidate_result_ref
            workflow_attribution["candidate_result_sha256"] = result_sha256
            candidate_result_errors.extend(
                validate_candidate_result_artifact(
                    run_dir / "manifest.json",
                    {
                        "workflow_attribution": workflow_attribution,
                        "status": status,
                        "exit_code": exit_code,
                    },
                )
            )
        if candidate_result_errors:
            with stderr_path.open("a", encoding="utf-8") as handle:
                handle.write("\ncandidate result validation failed: " + "; ".join(candidate_result_errors) + "\n")
            if exit_code == 0:
                exit_code = 3
            status = "fail"
            blocked_reason = "candidate-result-invalid"
    completed_at = utc_now()
    duration_ms = int((time.monotonic() - started) * 1000)
    summary = args.summary or f"command exited {exit_code}"
    manifest = write_manifest(
        root=root,
        run_dir=run_dir,
        run_id=run_id,
        argv=command,
        exit_code=exit_code,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        summary=summary,
        linked_acceptance_ids=args.acceptance_id,
        linked_scenario_ids=args.scenario_id,
        blocked_reason=blocked_reason,
        workflow_attribution=workflow_attribution,
    )
    print(str(manifest.relative_to(root)))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
