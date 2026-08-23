#!/usr/bin/env python3
"""Shared, fail-open parsing for Codex tool-hook payloads."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PATCH_HEADER_RE = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to):\s*(.+?)\s*$")
DECLARED_VERIFIER_FIELDS = (
    "Main build command",
    "Service-specific build commands",
    "Main test command",
    "Focused test command",
    "E2E command",
)
FALLBACK_VERIFIER_PREFIXES = (
    "pytest",
    "python -m pytest",
    "python3 -m pytest",
    "npm test",
    "npm run test",
    "pnpm test",
    "pnpm run test",
    "yarn test",
    "go test",
    "cargo test",
    "mvn test",
    "mvn verify",
    "./mvnw test",
    "./mvnw verify",
    "gradle test",
    "./gradlew test",
    "make test",
    "make check",
)


@dataclass(frozen=True)
class PatchEnvelope:
    targets: tuple[str, ...]
    changed_lines: tuple[str, ...]
    command: str


def load_payload(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def payload_command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command")
    return command if isinstance(command, str) else ""


def is_apply_patch_payload(payload: dict[str, Any]) -> bool:
    return payload.get("tool_name") == "apply_patch" and bool(payload_command(payload))


def normalize_patch_path(value: str) -> str:
    normalized = value.strip().strip('"\'').replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return posixpath.normpath(normalized)


def parse_apply_patch(command: str) -> PatchEnvelope:
    targets: list[str] = []
    changed_lines: list[str] = []
    for raw_line in command.splitlines():
        header = PATCH_HEADER_RE.match(raw_line)
        if header:
            path = normalize_patch_path(header.group(2))
            if path and path != "." and path not in targets:
                targets.append(path)
            continue
        if raw_line.startswith(("+", "-")) and not raw_line.startswith(("+++", "---")):
            changed_lines.append(raw_line)
    return PatchEnvelope(tuple(targets), tuple(changed_lines), command)


def stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def normalized_command(command: str) -> str:
    return " ".join(command.strip().split())


def _walk_values(value: Any, *, depth: int = 0) -> Iterable[tuple[str, Any]]:
    if depth > 6:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from _walk_values(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child, depth=depth + 1)


def response_exit_code(payload: dict[str, Any]) -> int | None:
    response = payload.get("tool_response")
    codes: set[int] = set()
    for key, value in _walk_values(response):
        if key.lower() not in {"exit_code", "exitcode"}:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            codes.add(value)
        elif isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value.strip()):
            codes.add(int(value.strip()))
    if len(codes) == 1:
        return next(iter(codes))
    return None


def response_succeeded(payload: dict[str, Any]) -> bool | None:
    exit_code = response_exit_code(payload)
    if exit_code is not None:
        return exit_code == 0

    response = payload.get("tool_response")
    if isinstance(response, str):
        normalized = response.strip().lower()
        if normalized == "done!" or normalized.startswith("done!\n"):
            return True
        return None
    if not isinstance(response, dict):
        return None

    success = response.get("success")
    if isinstance(success, bool):
        return success
    status = response.get("status")
    if isinstance(status, str):
        normalized_status = status.strip().lower()
        if normalized_status in {"success", "succeeded", "completed", "ok", "pass", "passed"}:
            return True
        if normalized_status in {"error", "failed", "failure", "cancelled", "canceled"}:
            return False
    return None


def declared_verifier_prefixes(root: Path) -> tuple[str, ...]:
    conventions = root / ".agents" / "references" / "project-conventions.md"
    try:
        text = conventions.read_text(encoding="utf-8")
    except OSError:
        return ()

    prefixes: list[str] = []
    for field in DECLARED_VERIFIER_FIELDS:
        match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.*?)\s*$", text)
        if not match:
            continue
        value = match.group(1)
        spans = re.findall(r"(?<!`)`([^`\r\n]+)`(?!`)", value)
        if len(spans) != 1:
            continue
        candidate = normalized_command(spans[0])
        lowered = candidate.lower()
        if not candidate or re.search(r"(?:&&|\|\||[;&|<>]|\$\(|\r|\n)", candidate):
            continue
        if re.search(r"待填写|\b(?:todo|tbd|optional)\b|<[^>]+>|\{[^}]+\}|\[[^]]+\]", lowered):
            continue
        if candidate not in prefixes:
            prefixes.append(candidate)
    return tuple(prefixes)


def command_matches_prefix(command: str, prefix: str) -> bool:
    return command == prefix or command.startswith(prefix + " ")


def recognized_verifier(command: str, declared: tuple[str, ...]) -> tuple[bool, str]:
    normalized = normalized_command(command)
    for prefix in declared:
        if command_matches_prefix(normalized, prefix):
            return True, "declared"
    for prefix in FALLBACK_VERIFIER_PREFIXES:
        if command_matches_prefix(normalized, prefix):
            return True, "fallback"
    return False, "none"
