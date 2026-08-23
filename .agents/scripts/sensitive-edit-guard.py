#!/usr/bin/env python3
"""PreToolUse guard for apply_patch sensitive paths and review authorization."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import hook_event_contract as hook_contract
import markdown_document as md_doc
import sensitive_guard_policy as policy


STRICT_CURRENT = ".agent-state/flags/sensitive-guard-strict.enabled"
STRICT_LEGACY = ".agents/state/sensitive-guard-strict.enabled"
READ_ONLY_MODES = {"review-only", "plan-only"}
IMPLEMENTATION_MODE = "implementation-authorized"
IMPLEMENTATION_AUTH = {"task", "session"}
BOUNDARY_TRANSITION_FIELDS = {
    "mode",
    "write authorization",
    "authorization source",
    "allowed write scope",
    "prohibited actions",
    "finding disposition policy",
    "transition decision",
}
BOUNDARY_PLACEHOLDERS = {
    "",
    "none",
    "n/a",
    "na",
    "not-needed",
    "optional",
    "todo",
    "tbd",
}


def strict_enabled(root: Path, override: bool = False) -> bool:
    return override or os.getenv("CODEX_SENSITIVE_GUARD_STRICT") == "1" or any(
        (root / relative).is_file() for relative in (STRICT_CURRENT, STRICT_LEGACY)
    )

def review_boundary(root: Path) -> dict[str, str] | None:
    progress = root / "progress.md"
    try:
        text = progress.read_text(encoding="utf-8")
        section = md_doc.section_text(text, "Review / Audit Boundary")
        if not section:
            return None
        return md_doc.key_value_table(section)
    except (OSError, UnicodeError, ValueError):
        return None


def normalize_boundary_value(value: str | None) -> str:
    return (value or "").strip().strip("`").lower()


def concrete_boundary_value(value: str | None) -> bool:
    normalized = normalize_boundary_value(value)
    return normalized not in BOUNDARY_PLACEHOLDERS and "待填写" not in normalized


def safe_boundary_state(values: dict[str, str]) -> bool:
    mode = normalize_boundary_value(values.get("mode"))
    write_authorization = normalize_boundary_value(values.get("write authorization"))
    finding_policy = normalize_boundary_value(values.get("finding disposition policy"))
    transition_decision = normalize_boundary_value(values.get("transition decision"))
    if mode in READ_ONLY_MODES:
        return (
            write_authorization in {"none", "revoked", "not-needed"}
            and finding_policy in {"accepted-as-finding-only", "not-needed"}
            and transition_decision in {"stay-readonly", "ask-user", "not-needed"}
        )
    if mode == IMPLEMENTATION_MODE:
        return (
            write_authorization in IMPLEMENTATION_AUTH
            and concrete_boundary_value(values.get("authorization source"))
            and concrete_boundary_value(values.get("allowed write scope"))
            and finding_policy == "implementation-approved"
            and transition_decision == "implement-authorized"
        )
    return False


def boundary_transition_only(envelope: hook_contract.PatchEnvelope, current_values: dict[str, str]) -> bool:
    if envelope.targets != ("progress.md",):
        return False
    patch_lines = envelope.command.splitlines()
    if sum(1 for line in patch_lines if line.startswith("@@")) != 1:
        return False
    if "## Review / Audit Boundary" not in patch_lines:
        return False
    removed: dict[str, str] = {}
    added: dict[str, str] = {}
    for raw in envelope.changed_lines:
        line = raw[1:].strip()
        if not line:
            continue
        if line == "## Review / Audit Boundary" or re.fullmatch(r"\|?\s*:?-{3,}:?\s*\|.*", line):
            continue
        if not line.startswith("|") or line.count("|") < 3:
            return False
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            return False
        key = cells[0].lower()
        if key in {"item", "field"}:
            continue
        if key not in BOUNDARY_TRANSITION_FIELDS:
            return False
        target = added if raw.startswith("+") else removed
        if key in target:
            return False
        target[key] = cells[1]

    if not added:
        return False
    prospective = dict(current_values)
    for key, value in removed.items():
        if key not in prospective or normalize_boundary_value(prospective[key]) != normalize_boundary_value(value):
            return False
        prospective.pop(key)
    for key, value in added.items():
        if key in prospective:
            return False
        prospective[key] = value
    return safe_boundary_state(prospective)


def authorization_tuple_valid(root: Path) -> bool:
    validator = Path(__file__).resolve().with_name("validate-review-authorization.py")
    if not validator.is_file() or not (root / "task_plan.md").is_file():
        return False
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--root",
                str(root),
                "--strict-trigger",
                "--format",
                "json",
            ],
            text=True,
            capture_output=True,
            # Keep the nested authoritative check inside the 300 ms pre-edit
            # event budget. A timeout is treated as an invalid tuple (block),
            # never as authorization.
            timeout=0.25,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def authorization_block(root: Path, envelope: hook_contract.PatchEnvelope) -> tuple[str, str] | None:
    values = review_boundary(root)
    if values is None:
        return None
    mode = normalize_boundary_value(values.get("mode"))
    write_authorization = normalize_boundary_value(values.get("write authorization"))

    if mode in READ_ONLY_MODES or write_authorization == "revoked":
        if boundary_transition_only(envelope, values):
            return None
        return (
            "authorization-boundary",
            "Review / Audit Boundary is explicitly read-only or revoked. Only a boundary-table-only progress.md transition may proceed; do not combine it with business/source edits.",
        )

    if mode == IMPLEMENTATION_MODE:
        if write_authorization not in IMPLEMENTATION_AUTH or not authorization_tuple_valid(root):
            if boundary_transition_only(envelope, values):
                return None
            return (
                "authorization-tuple-invalid",
                "Mode=implementation-authorized requires the complete Review / Audit Boundary tuple to pass validate-review-authorization.py before an edit proceeds.",
            )
    return None


def emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard apply_patch sensitive paths and explicit review boundaries.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root).resolve()
    payload = hook_contract.load_payload(sys.stdin.read())
    if not hook_contract.is_apply_patch_payload(payload):
        return 0
    envelope = hook_contract.parse_apply_patch(hook_contract.payload_command(payload))
    if not envelope.targets:
        return 0

    hardline_rules: set[str] = set()
    if any(policy.hardline_git_state(path) for path in envelope.targets):
        hardline_rules.add("git-managed-state")
    hardline_rules.update(policy.patch_content_hardline_rule_ids(envelope.command))
    if hardline_rules:
        message = (
            "[sensitive-edit-guard] hardline block: "
            + ", ".join(sorted(hardline_rules))
            + ". Use the owning git operation or a user-controlled secret workflow; do not edit this material through apply_patch."
        )
        emit(
            {
                "decision": "block",
                "reason": message,
                "hardline": True,
                "edit_guard_severity": "hardline",
                "edit_guard_rule": sorted(hardline_rules)[0],
            }
        )
        return 0

    auth_block = authorization_block(root, envelope)
    if auth_block is not None:
        rule, reason = auth_block
        emit(
            {
                "decision": "block",
                "reason": "[sensitive-edit-guard] " + reason,
                "hardline": False,
                "edit_guard_severity": "authorization-block",
                "edit_guard_rule": rule,
            }
        )
        return 0

    path_rules: set[str] = set()
    for path in envelope.targets:
        path_rules.update(policy.edit_path_rule_ids(path))
    if not path_rules:
        return 0

    message = (
        "[sensitive-edit-guard] sensitive edit signal: "
        + ", ".join(sorted(path_rules))
        + ". Confirm scope, validation, rollback, and the progress.md Sensitive Operations record before proceeding."
    )
    if strict_enabled(root, args.strict):
        emit(
            {
                "decision": "block",
                "reason": message,
                "hardline": False,
                "edit_guard_severity": "strict-block",
                "edit_guard_rule": sorted(path_rules)[0],
            }
        )
    else:
        emit(
            {
                "systemMessage": message,
                "hardline": False,
                "edit_guard_severity": "warning",
                "edit_guard_rule": sorted(path_rules)[0],
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
