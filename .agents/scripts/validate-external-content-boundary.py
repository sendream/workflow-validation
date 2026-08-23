#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXTERNAL_SOURCE_KINDS = {
    "web_page",
    "search_result",
    "browser_page",
    "official_doc",
    "paper",
    "pdf",
    "image",
    "mcp_resource",
    "mcp_tool_description",
    "tool_description",
    "tool_output",
    "stdout",
    "stderr",
    "log",
    "external_skill_description",
    "reviewer_output",
    "third_party_advice",
    "archive_summary",
}

FORBIDDEN_AUTHORIZATIONS = {
    "tool_call",
    "connector_read",
    "repo_write",
    "write_files",
    "deploy",
    "push",
    "db_action",
    "db_write",
    "external_write",
    "secrets_access",
    "workflow_rule_change",
    "commit",
    "destructive_command",
}

ALLOWED_DERIVED_OUTPUTS = {
    "fact",
    "risk_candidate",
    "verification_candidate",
    "tool_candidate",
    "reviewer_finding",
    "untrusted_instruction",
    "ignored_instruction",
}

DANGEROUS_INSTRUCTION_PATTERNS = [
    ("repo_write", re.compile(r"\b(patch|modify|edit|write)\s+(files?|code|repo|source)\b", re.I)),
    ("push", re.compile(r"\b(git\s+push|push\s+(now|--force)|force[- ]push)\b", re.I)),
    ("deploy", re.compile(r"\bdeploy(ment)?\b", re.I)),
    ("db_action", re.compile(r"\b(apply\s+db\s+migration|database\s+(write|update|delete)|db\s+(write|update|delete|migration))\b", re.I)),
    ("secrets_access", re.compile(r"\b(read|access|leak|print)\s+(secrets?|tokens?|credentials?)\b", re.I)),
    ("workflow_rule_change", re.compile(r"\b(update|change|override)\s+(agents\.md|workflow\s+rules?)\b", re.I)),
    ("destructive_command", re.compile(r"\b(rm\s+-rf|mkfs|dd\s+if=|chmod\s+-r|chown\s+-r)\b", re.I)),
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [clean(item) for item in value if clean(item)]
    text = clean(value)
    return [text] if text else []


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"input not found: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"input is not valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["input must be a JSON object"]
    return payload, []


def authority_like_summary(text: str) -> str | None:
    for label, pattern in DANGEROUS_INSTRUCTION_PATTERNS:
        if pattern.search(text):
            return label
    return None


def validate(root: Path, input_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not is_under(input_path, root):
        errors.append("input must stay inside project root")
        return {
            "status": "fail",
            "input": str(input_path),
            "records": 0,
            "errors": errors,
            "warnings": warnings,
        }

    payload, load_errors = load_json(input_path)
    errors.extend(load_errors)
    if payload is None:
        return {
            "status": "fail",
            "input": str(input_path),
            "records": 0,
            "errors": errors,
            "warnings": warnings,
        }

    records = payload.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records must be a non-empty list")
        records = []

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"record {index}: must be an object")
            continue

        source_kind = clean(record.get("source_kind"))
        if source_kind not in EXTERNAL_SOURCE_KINDS:
            errors.append(f"record {index}: unknown or non-external source_kind: {source_kind or '<empty>'}")
            continue

        authorizes = set(as_list(record.get("authorizes")))
        requested_actions = set(as_list(record.get("requested_actions")))
        if authorizes:
            blocked = sorted(authorizes & FORBIDDEN_AUTHORIZATIONS)
            unknown = sorted(authorizes - FORBIDDEN_AUTHORIZATIONS)
            if blocked:
                errors.append(
                    f"record {index}: untrusted external content cannot authorize {', '.join(blocked)}"
                )
            if unknown:
                errors.append(
                    f"record {index}: external content must not grant unknown authority values: {', '.join(unknown)}"
                )
        if requested_actions:
            blocked = sorted(requested_actions & FORBIDDEN_AUTHORIZATIONS)
            if blocked:
                errors.append(
                    f"record {index}: untrusted external content cannot authorize requested action {', '.join(blocked)}"
                )

        derived_outputs = set(as_list(record.get("derived_outputs")))
        if not derived_outputs:
            errors.append(f"record {index}: derived_outputs must classify the content boundary")
        elif not derived_outputs <= ALLOWED_DERIVED_OUTPUTS:
            bad = sorted(derived_outputs - ALLOWED_DERIVED_OUTPUTS)
            errors.append(f"record {index}: unsupported derived_outputs values: {', '.join(bad)}")

        ignored = clean(record.get("ignored_instruction"))
        summary_action = authority_like_summary(clean(record.get("summary")))
        if (requested_actions or authorizes or summary_action) and not ignored:
            errors.append(
                f"record {index}: authority-like external instruction must be recorded as ignored_instruction"
            )

    return {
        "status": "pass" if not errors else "fail",
        "input": str(input_path),
        "records": len(records),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that external content/tool output is treated as data and cannot grant workflow authority."
    )
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--input", required=True, help="Boundary JSON artifact relative to root or absolute path.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root).resolve()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = root / input_path
    result = validate(root, input_path.resolve())

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        for error in result.get("errors", []):
            print(f"error: {error}")
        for warning in result.get("warnings", []):
            print(f"warning: {warning}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
