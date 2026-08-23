#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


PLACEHOLDERS = {"", "待填写", "pending", "missing", "required", "unknown", "todo", "tbd"}
DEFAULT_RELATIVE_TARGETS = ("AGENTS.md", "code_review.md", ".agents/references")
TEXT_SUFFIXES = {".md", ".mdx", ".txt", ".rst"}
DENIED_PREFIXES = (
    ".git",
    ".agent-state",
    ".agents/tasks",
    ".agents/runs",
    "graphify-out",
    "codegraph-out",
    ".codegraph",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
)
REQUIRED_REFERENCE_METADATA = ("Last updated", "Owner", "Source of truth", "Refresh when")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SUSPICIOUS_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction-override",
        re.compile(
            r"\b(ignore|disregard|override|bypass|disable|forget)\b.{0,80}\b(previous|above|system|developer|user|agents?\.md|instructions?|rules?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "secret-exfiltration",
        re.compile(
            r"\b(reveal|leak|exfiltrate|send|upload|copy|print|dump)\b.{0,80}\b(secrets?|tokens?|credentials?|private keys?|\.env|id_rsa|pem)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "approval-bypass",
        re.compile(
            r"\b(skip|bypass|disable|ignore)\b.{0,80}\b(approval|validator|gate|permission|review|sandbox)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "persona-jailbreak",
        re.compile(r"\b(developer mode|jailbreak|DAN mode|ignore safety|unrestricted agent)\b", re.IGNORECASE),
    ),
)
NEGATION_TERMS = (
    "do not",
    "don't",
    "must not",
    "should not",
    "cannot",
    "can't",
    "is not",
    "are not",
    "not a",
    "no ",
    "forbid",
    "forbidden",
    "never",
    "禁止",
    "不得",
    "不能",
    "不要",
    "不是",
    "不允许",
)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        text = text[1:-1]
    return text.strip()


def is_placeholder(value: Any) -> bool:
    normalized = clean(value).lower()
    return normalized in PLACEHOLDERS or "待填写" in normalized


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def denied_path(root: Path, path: Path) -> str | None:
    if not is_under(path, root):
        return "outside project root"
    rel = display_path(root, path)
    for prefix in DENIED_PREFIXES:
        if rel == prefix or rel.startswith(prefix + "/"):
            return f"generated/runtime/archive path is not a context-reference target: {prefix}"
    return None


def candidate_files(root: Path, values: list[str]) -> tuple[list[Path], list[str]]:
    errors: list[str] = []
    files: list[Path] = []
    targets = values or list(DEFAULT_RELATIVE_TARGETS)
    using_defaults = not values
    for value in targets:
        raw = Path(value)
        path = raw if raw.is_absolute() else root / raw
        denial = denied_path(root, path)
        if denial:
            errors.append(f"{value}: {denial}")
            continue
        if path.is_file():
            if path.suffix.lower() in TEXT_SUFFIXES or path.name == "AGENTS.md":
                files.append(path.resolve())
            continue
        if path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES:
                    nested_denial = denied_path(root, candidate)
                    if not nested_denial:
                        files.append(candidate.resolve())
            continue
        if not using_defaults:
            errors.append(f"{value}: target not found")
    return sorted(set(files)), errors


def metadata_value(text: str, key: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    return clean(match.group(1)) if match else ""


def is_reference_path(path: Path) -> bool:
    return ".agents/references" in path.as_posix()


def match_is_negated(line: str, match_start: int) -> bool:
    lowered = line.lower()
    prefix = lowered[max(0, match_start - 32) : match_start]
    return any(term in prefix for term in NEGATION_TERMS)


def suspicious_lines(path: Path, root: Path, text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in SUSPICIOUS_RULES:
            match = pattern.search(line)
            if match and not match_is_negated(line, match.start()):
                matches.append(
                    {
                        "path": display_path(root, path),
                        "line": line_no,
                        "rule": rule_id,
                        "text": line.strip()[:180],
                    }
                )
                break
    return matches


def validate_file(root: Path, path: Path, strict: bool, max_age_days: int | None) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{display_path(root, path)}: not UTF-8 text"], warnings, []

    suspicious = suspicious_lines(path, root, text)
    for item in suspicious:
        message = f"{item['path']}:{item['line']}: suspicious {item['rule']} context line"
        if strict:
            errors.append(message)
        else:
            warnings.append(message)

    if is_reference_path(path):
        for key in REQUIRED_REFERENCE_METADATA:
            value = metadata_value(text, key)
            if is_placeholder(value):
                message = f"{display_path(root, path)}: missing reference metadata field {key}"
                if strict:
                    errors.append(message)
                else:
                    warnings.append(message)
        last_updated = metadata_value(text, "Last updated")
        if last_updated and not is_placeholder(last_updated):
            if not ISO_DATE_RE.fullmatch(last_updated):
                warnings.append(f"{display_path(root, path)}: Last updated should use YYYY-MM-DD")
            elif max_age_days is not None:
                try:
                    updated = date.fromisoformat(last_updated)
                    age = (date.today() - updated).days
                except ValueError:
                    age = -1
                if age > max_age_days:
                    message = f"{display_path(root, path)}: reference metadata is stale ({age} days > {max_age_days})"
                    if strict:
                        errors.append(message)
                    else:
                        warnings.append(message)
    return errors, warnings, suspicious


def validate(root: Path, paths: list[str], strict: bool, max_age_days: int | None) -> dict[str, Any]:
    files, target_errors = candidate_files(root, paths)
    errors = list(target_errors)
    warnings: list[str] = []
    suspicious: list[dict[str, Any]] = []

    for path in files:
        file_errors, file_warnings, file_suspicious = validate_file(root, path, strict, max_age_days)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
        suspicious.extend(file_suspicious)

    return {
        "status": "pass" if not errors else "fail",
        "checked_files": [display_path(root, path) for path in files],
        "suspicious_matches": suspicious,
        "errors": errors,
        "warnings": warnings,
        "strict": strict,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AGENTS.md and .agents/references context files for prompt-injection-like lines and reference metadata freshness."
    )
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Context/reference file or directory to scan. Defaults to AGENTS.md and .agents/references.",
    )
    parser.add_argument("--strict", action="store_true", help="Fail on suspicious context lines or missing reference metadata.")
    parser.add_argument("--max-age-days", type=int, default=None, help="Warn/fail when Last updated is older than this many days.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    payload = validate(root, args.path, args.strict, args.max_age_days)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        for warning in payload["warnings"]:
            print(f"warning: {warning}")
        for error in payload["errors"]:
            print(f"error: {error}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
