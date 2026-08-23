#!/usr/bin/env python3
"""Shared child-validator result envelope and fail-closed JSON execution."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ACCEPTED_PAYLOAD_STATUSES = {"pass", "skipped", "warn", "risk-accepted"}


@dataclass(frozen=True)
class ChildValidatorResult:
    name: str
    command: list[str]
    returncode: int
    status: str
    json: dict[str, Any] | None
    stdout: str
    stderr: str
    timed_out: bool = False
    parse_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_json_validator(
    name: str,
    command: list[str],
    cwd: Path,
    *,
    timeout: float | None = None,
) -> ChildValidatorResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ChildValidatorResult(
            name=name,
            command=command,
            returncode=124,
            status="fail",
            json=None,
            stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            timed_out=True,
            parse_error="timeout",
        )

    payload: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        decoded = json.loads(completed.stdout)
        if isinstance(decoded, dict):
            payload = decoded
        else:
            parse_error = "JSON payload must be an object"
    except json.JSONDecodeError as exc:
        parse_error = f"invalid JSON: {exc.msg}"

    payload_status = str(payload.get("status", "")).strip().lower() if payload else ""
    accepted = completed.returncode == 0 and parse_error is None and payload_status in ACCEPTED_PAYLOAD_STATUSES
    return ChildValidatorResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        status="pass" if accepted else "fail",
        json=payload,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        parse_error=parse_error,
    )
