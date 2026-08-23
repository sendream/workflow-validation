#!/usr/bin/env python3
"""Validate a local capability card as an admission record, never enablement."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from markdown_table import MarkdownTableError, parse_markdown_tables


REQUIRED_FIELDS = {
    "purpose",
    "owner",
    "source_digest",
    "trust",
    "scopes",
    "limits",
    "approval",
    "isolation",
    "evidence",
    "rollback",
    "idempotency",
    "expiry",
}
TRUSTED_SOURCES = {"verified-local", "project-owner", "official-source"}
TASK_LEVEL_APPROVAL = "task-level-explicit"
WRITE_SCOPES = {"repo-write", "external-write"}
CANONICAL_SCOPE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SENSITIVE_CONTEXT_RE = re.compile(
    r"(?:\b(?:secret|secrets|token|tokens|password|credential|credentials|cookie|cookies)\b"
    r"|\bapi[\s_-]*key\b|\bprivate[\s_-]*key\b|(?<![\w.-])\.env\b)",
    re.IGNORECASE,
)
WRITE_SCOPE_RE = re.compile(
    r"(?:^|[-_/ ])(?:write|mutate|delete|create|update|deploy|publish)(?:$|[-_/ ])",
    re.IGNORECASE,
)
MULTI_AGENT_SCOPE = "multi-agent"
SECRET_CONTEXT_FIELDS = ("scopes", "limits", "isolation")
EMPTY_QUALIFICATION_VALUES = {"", "none", "not-needed", "not applicable", "n/a"}


def normalized(value: str) -> str:
    return " ".join(value.strip().lower().split())


def parse_card(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"cannot read card: {exc}"]
    if not re.search(r"^#\s+Capability Card\b", text, re.IGNORECASE | re.MULTILINE):
        errors.append("card must start with a Capability Card heading")
    try:
        tables = parse_markdown_tables(text, strict=True)
    except MarkdownTableError as exc:
        return {}, [f"malformed capability card table: {exc}"]
    table = next(
        (
            item
            for item in tables
            if [header.strip().lower() for header in item.headers] == ["field", "value"]
        ),
        None,
    )
    if table is None:
        return {}, [*errors, "capability card requires a field/value table"]
    fields: dict[str, str] = {}
    for row in table.rows:
        if len(row) != 2:
            errors.append("capability card rows must have exactly two columns")
            continue
        key = normalized(row[0]).replace(" ", "_")
        if not key:
            errors.append("capability card has an empty field")
            continue
        if key in fields:
            errors.append(f"capability card repeats field: {key}")
            continue
        fields[key] = row[1].strip()
    return fields, errors


def validate_fields(fields: dict[str, str]) -> list[str]:
    errors: list[str] = []
    missing = sorted(field for field in REQUIRED_FIELDS if not fields.get(field, "").strip())
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
        return errors

    source_digest = fields["source_digest"].strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", source_digest):
        errors.append("source_digest must be sha256:<64 lowercase hex>")

    trust = normalized(fields["trust"])
    if trust not in TRUSTED_SOURCES:
        errors.append("untrusted or unknown source cannot act as a capability authority")

    approval = normalized(fields["approval"])
    if approval != TASK_LEVEL_APPROVAL:
        errors.append("approval must be task-level-explicit; a card never grants standing permission")

    scopes = {normalized(item) for item in fields["scopes"].split(",") if normalized(item)}
    if not scopes:
        errors.append("scopes must declare at least one bounded scope")
    invalid_scopes = sorted(scope for scope in scopes if not CANONICAL_SCOPE_RE.fullmatch(scope))
    if invalid_scopes:
        errors.append("scopes must use lowercase hyphen-delimited identifiers: " + ", ".join(invalid_scopes))
    if any(SENSITIVE_CONTEXT_RE.search(fields[name]) for name in SECRET_CONTEXT_FIELDS):
        errors.append("capability cards must not permit secrets in model context or scope")

    expiry = fields["expiry"].strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expiry):
        errors.append("expiry must be an ISO-8601 date (YYYY-MM-DD)")
    else:
        try:
            expiry_date = date.fromisoformat(expiry)
        except ValueError:
            errors.append("expiry must be a real ISO-8601 calendar date")
        else:
            today = datetime.now(timezone.utc).date()
            if expiry_date < today:
                errors.append("expiry must not be before the current UTC date")

    write_capable = bool(WRITE_SCOPES.intersection(scopes)) or any(WRITE_SCOPE_RE.search(scope) for scope in scopes)
    if write_capable:
        rollback = normalized(fields["rollback"])
        idempotency = normalized(fields["idempotency"])
        if rollback in {"", "none", "not-needed", "not applicable", "n/a"}:
            errors.append("write-capable cards require a concrete rollback")
        if idempotency not in {"idempotent", "compensating-action"}:
            errors.append("write-capable cards require idempotency or a compensating action")

    if MULTI_AGENT_SCOPE in scopes:
        qualification = normalized(fields.get("qualification", ""))
        if qualification in EMPTY_QUALIFICATION_VALUES:
            errors.append("multi-agent cards require a concrete qualification reference")
    return errors


def validate_card(root: Path, card: Path) -> dict[str, object]:
    errors: list[str] = []
    try:
        resolved_root = root.resolve()
        resolved_card = card.resolve()
        relative = resolved_card.relative_to(resolved_root).as_posix()
    except ValueError:
        relative = str(card)
        errors.append("card path must stay under --root")
        resolved_card = card

    fields: dict[str, str] = {}
    if not errors:
        fields, parse_errors = parse_card(resolved_card)
        errors.extend(parse_errors)
        errors.extend(validate_fields(fields))

    scopes = [normalized(item) for item in fields.get("scopes", "").split(",") if normalized(item)]
    return {
        "status": "fail" if errors else "pass",
        "card": relative,
        "errors": errors,
        "declared_scopes": scopes,
        "admission_only": True,
        "permission_changed": False,
        "requires_task_level_authorization": True,
        "requires_multi_agent_qualification": MULTI_AGENT_SCOPE in scopes,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root used to bound card paths")
    parser.add_argument("--card", required=True, help="Capability-card Markdown file under --root")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = validate_card(Path(args.root), Path(args.card))
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        print("admission_only: true")
        print("permission_changed: false")
        for error in payload["errors"]:
            print(f"error: {error}", file=sys.stderr)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
