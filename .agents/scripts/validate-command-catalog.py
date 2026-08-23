#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc
import markdown_table as md_table


VALID_KINDS = {"prompt-snippet", "command-contract", "reviewer-prompt", "translation-contract"}
VALID_STATUSES = {"disabled", "trial", "available"}
VALID_SCOPES = {"repo-read", "report-write-only", "implementation-authorized"}
REQUIRED_METADATA_FIELDS = (
    "id",
    "kind",
    "status",
    "description",
    "trigger",
    "non_trigger",
    "scope",
    "requires_explicit_authorization",
    "source_of_truth",
    "refresh_when",
)
REQUIRED_PERMISSION_FIELDS = ("repo_read", "repo_write", "external_read", "external_write", "network")
FORBIDDEN_RUNTIME_PATTERNS = (
    re.compile(r"(?m)(?:^|[\s|>`-])!\s*[A-Za-z0-9_./-]+"),
    re.compile(r"(?im)(?:^|\|\s*|[{\[,]\s*['\"]?|\-\s*)(?:model|subtask)\s*['\"]?\s*[:|=]"),
    re.compile(r"(?im)(?:^|\|\s*|[{\[,]\s*['\"]?|\-\s*)mode\s*['\"]?\s*[:|=]\s*['\"]?subagent\b"),
)
FORBIDDEN_STATE_TERMS = (
    "second progress",
    "second state source",
    "workflow runner",
    "auto-run",
    "autorun",
    "auto run",
)
NEGATION_TERMS = (
    "not ",
    "not a ",
    "does not",
    "do not",
    "must not",
    "cannot",
    "can't",
    "no ",
    "forbid",
    "forbidden",
    "禁止",
    "不得",
    "不能",
    "不是",
)
PATH_ESCAPE_PATTERN = re.compile(
    r"(?i)(?:^|[\s|])(?:/|[a-z]:[\\/]|\\\\)|(?:^|[\\/])\.\.(?:[\\/]|$)"
)
MARKDOWN_LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")


def clean(value: str) -> str:
    return md_table.clean_cell(value)


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def normalize_value(value: Any) -> str:
    return clean(str(value)).lower().replace(" ", "-").replace("_", "-")


def is_placeholder(value: Any, *, allow_not_needed: bool = False) -> bool:
    text = clean(str(value)).lower()
    if allow_not_needed and text in {"not-needed", "none"}:
        return False
    return (
        not text
        or text in {"todo", "tbd", "pending", "missing", "required", "optional", "待填写"}
        or "待填写" in text
        or text.startswith("optional /")
    )


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=True,
        normalize_key=normalize_key,
    )


def field_table(markdown_text: str, heading: str) -> dict[str, str]:
    rows = extract_table(markdown_text, heading)
    return {normalize_key(row.get("field", "")): row.get("value", "") for row in rows}


def boolish(value: str) -> bool:
    return clean(value).lower() in {"true", "yes", "required", "enabled"}


def has_external_or_write_permission(permissions: dict[str, str]) -> bool:
    network = clean(permissions.get("network", "")).lower()
    return (
        boolish(permissions.get("repo_write", ""))
        or boolish(permissions.get("external_read", ""))
        or boolish(permissions.get("external_write", ""))
        or network not in {"", "none", "not-needed"}
    )


def has_unnegated_forbidden_state(text: str) -> bool:
    for line in text.splitlines():
        normalized = line.strip().lower()
        if not normalized:
            continue
        if not any(term in normalized for term in FORBIDDEN_STATE_TERMS):
            continue
        if any(term in normalized for term in NEGATION_TERMS):
            continue
        return True
    return False


def unsafe_path_value(value: str) -> bool:
    normalized = clean(value)
    if not normalized or normalized.lower() in {"none", "not-needed"}:
        return False
    values = [normalized] + [clean(target) for target in MARKDOWN_LINK_TARGET_RE.findall(normalized)]
    for candidate in values:
        lowered = candidate.lower()
        if "://" in lowered or lowered.startswith("file:"):
            return True
        if "codex-home" in lowered:
            return True
        if bool(PATH_ESCAPE_PATTERN.search(candidate)):
            return True
        path = Path(candidate)
        if path.is_absolute() or ".." in path.parts:
            return True
    return False


def validate_contract(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for pattern in FORBIDDEN_RUNTIME_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path.name}: contract must not embed runtime shell expansion, model, subtask, or subagent execution fields")
            break

    try:
        metadata = field_table(text, "## Contract Metadata")
        permissions = field_table(text, "## Permissions")
        trigger_rows = extract_table(text, "## Trigger Eval")
        outputs = field_table(text, "## Outputs")
    except md_table.MarkdownTableError as exc:
        errors.append(f"{path.name}: {exc}")
        return errors

    for field in REQUIRED_METADATA_FIELDS:
        if is_placeholder(metadata.get(field, "")):
            errors.append(f"{path.name}: Contract Metadata missing {field}")
    for field in REQUIRED_PERMISSION_FIELDS:
        if is_placeholder(permissions.get(field, ""), allow_not_needed=field == "network"):
            errors.append(f"{path.name}: Permissions missing {field}")

    contract_id = normalize_value(metadata.get("id", ""))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", contract_id):
        errors.append(f"{path.name}: id must be hyphen-case")
    kind = normalize_value(metadata.get("kind", ""))
    if kind not in VALID_KINDS:
        errors.append(f"{path.name}: kind must be one of {', '.join(sorted(VALID_KINDS))}")
    status = normalize_value(metadata.get("status", ""))
    if status not in VALID_STATUSES:
        errors.append(f"{path.name}: status must be disabled/trial/available")
    scope = normalize_value(metadata.get("scope", ""))
    if scope not in VALID_SCOPES:
        errors.append(f"{path.name}: scope must be repo-read/report-write-only/implementation-authorized")

    if status == "available" and has_external_or_write_permission(permissions):
        errors.append(f"{path.name}: available contracts must not request repo-write, external access, or network by default")
    if has_external_or_write_permission(permissions) and normalize_value(metadata.get("requires_explicit_authorization", "")) != "yes":
        errors.append(f"{path.name}: repo-write, external access, or network requires requires_explicit_authorization=yes")

    trigger_kinds = {normalize_value(row.get("case", row.get("type", ""))) for row in trigger_rows}
    if "positive" not in trigger_kinds or "negative" not in trigger_kinds:
        errors.append(f"{path.name}: Trigger Eval must include positive and negative prompts")

    artifact_value = outputs.get("artifacts_allowed", "")
    if unsafe_path_value(artifact_value):
        errors.append(f"{path.name}: artifacts_allowed must not point outside the repo, use absolute paths, URLs, Windows paths, parent traversal, or global Codex Home")

    if has_unnegated_forbidden_state(text):
        errors.append(f"{path.name}: contract must not create a runner or second state source")

    return errors


def validate_catalog(path: Path, root: Path) -> tuple[list[str], list[Path]]:
    if not path.exists():
        return [f"catalog not found: {path}"], []
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    contract_paths: list[Path] = []
    if "not a runner" not in text.lower() or "not a skill" not in text.lower():
        errors.append(f"{path.name}: catalog must state it is not a runner and not a skill")
    try:
        rows = extract_table(text, "## Catalog")
    except md_table.MarkdownTableError as exc:
        errors.append(f"{path.name}: {exc}")
        return errors, contract_paths
    for index, row in enumerate(rows, start=1):
        contract_id = normalize_value(row.get("id", ""))
        kind = normalize_value(row.get("kind", ""))
        status = normalize_value(row.get("status", ""))
        if contract_id == "not-needed":
            continue
        contract_path = clean(row.get("contract_path", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", contract_id):
            errors.append(f"{path.name}: Catalog row {index} id must be hyphen-case or not-needed")
        if kind not in VALID_KINDS:
            errors.append(f"{path.name}: Catalog row {index} kind is invalid")
        if status not in VALID_STATUSES:
            errors.append(f"{path.name}: Catalog row {index} status must be disabled/trial/available")
        if is_placeholder(contract_path):
            errors.append(f"{path.name}: Catalog row {index} contract_path is missing")
            continue
        if unsafe_path_value(contract_path):
            errors.append(f"{path.name}: Catalog row {index} contract_path must be repo-relative and stay inside the project")
            continue
        contract = Path(contract_path)
        if contract.is_absolute():
            errors.append(f"{path.name}: Catalog row {index} contract_path must be relative")
            continue
        resolved = (root / contract).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{path.name}: Catalog row {index} contract_path escapes project root")
            continue
        if not resolved.is_file():
            errors.append(f"{path.name}: Catalog row {index} contract_path does not exist: {contract_path}")
            continue
        contract_paths.append(resolved)
    return errors, contract_paths


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="validate-command-catalog: validate optional prompt snippet / command contract catalog without executing commands.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--catalog", default=".agents/references/command-catalog.md", help="Command catalog markdown file.")
    parser.add_argument("--contract", action="append", default=[], help="Contract markdown file. May be supplied multiple times.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    errors: list[str] = []
    catalog = Path(args.catalog)
    if not catalog.is_absolute():
        catalog = root / catalog
    catalog_errors, catalog_contracts = validate_catalog(catalog, root)
    errors.extend(catalog_errors)

    contract_paths: list[Path] = []
    for value in args.contract:
        contract = Path(value)
        if not contract.is_absolute():
            contract = root / contract
        contract_paths.append(contract.resolve())
    for contract in catalog_contracts:
        if contract.resolve() not in contract_paths:
            contract_paths.append(contract.resolve())

    for contract in contract_paths:
        if not contract.is_file():
            errors.append(f"contract not found: {contract}")
            continue
        errors.extend(validate_contract(contract))

    payload = {"status": "pass" if not errors else "fail", "errors": errors}
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        for error in errors:
            print(f"error: {error}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
