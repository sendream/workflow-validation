#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc
import markdown_table as md_table


PLACEHOLDERS = {"", "none", "not-needed", "n/a", "na", "待填写", "pending", "missing", "required"}
SKIP_DISPOSITIONS = {"not-needed", "still-future-work", "accepted-stale", "deferred"}
EVIDENCE_REQUIRED_SKIP_DISPOSITIONS = {"accepted-stale", "deferred"}
DENIED_SCAN_PREFIXES = (
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
    ".nuxt",
    "out",
    "target",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "tmp",
    "temp",
    "logs",
)
TEXT_SUFFIXES = {
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
}


def clean(value: str) -> str:
    return md_table.clean_cell(value)


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("/", "_")


def is_placeholder(value: str) -> bool:
    normalized = clean(value).lower()
    return normalized in PLACEHOLDERS or "待填写" in normalized


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=False,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def row_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row:
            return clean(row.get(key, ""))
    return ""


def path_tokens(value: str) -> list[str]:
    return [part.strip() for part in value.replace("，", ",").replace(";", ",").split(",") if part.strip()]


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def denied_scan_path(root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "outside project root"
    for prefix in DENIED_SCAN_PREFIXES:
        if relative == prefix or relative.startswith(prefix + "/"):
            return f"denied generated/runtime/archive path: {prefix}"
    return None


def token_policy_error(root: Path, token: str) -> str | None:
    normalized_token = token.replace("\\", "/").strip()
    while normalized_token.startswith("./"):
        normalized_token = normalized_token[2:]
    raw = Path(normalized_token)
    if normalized_token in {".", "", "**", "**/*", "**/*.md", "**/*.mdx"} or normalized_token.startswith("**/"):
        return "broad repo-wide scan paths are not allowed; provide explicit docs/tests paths"
    if raw.is_absolute() and not is_within(raw, root):
        return "absolute scan paths outside project root are not allowed"
    if ".." in raw.parts:
        return "parent-directory scan paths are not allowed"
    base = raw if raw.is_absolute() else root / normalized_token
    denial = denied_scan_path(root, base)
    if denial:
        return denial
    for prefix in DENIED_SCAN_PREFIXES:
        if normalized_token == prefix or normalized_token.startswith(prefix + "/"):
            return f"denied generated/runtime/archive scan path: {prefix}"
    return None


def scan_path_policy_errors(root: Path, scan_paths: str) -> list[str]:
    errors: list[str] = []
    for token in path_tokens(scan_paths):
        policy_error = token_policy_error(root, token)
        if policy_error:
            errors.append(f"{token}: {policy_error}")
    return errors


def candidate_files(root: Path, token: str) -> tuple[list[Path], list[str]]:
    policy_error = token_policy_error(root, token)
    if policy_error:
        return [], [policy_error]
    raw = Path(token)
    if raw.is_absolute():
        base = raw
    else:
        base = root / raw

    matches: list[Path] = []
    errors: list[str] = []
    if any(ch in token for ch in "*?[]"):
        if raw.is_absolute():
            try:
                pattern = raw.relative_to(root.resolve()).as_posix()
            except ValueError:
                return [], ["absolute scan paths outside project root are not allowed"]
        else:
            pattern = token.replace("\\", "/")
            while pattern.startswith("./"):
                pattern = pattern[2:]
        matches.extend(path for path in root.glob(pattern) if path.is_file())
    elif base.is_file():
        matches.append(base)
    elif base.is_dir():
        matches.extend(path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
    safe_matches: list[Path] = []
    for path in sorted(set(path.resolve() for path in matches)):
        denial = denied_scan_path(root, path)
        if denial:
            errors.append(denial)
            continue
        safe_matches.append(path)
    return safe_matches, errors


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def find_phrase(root: Path, phrase: str, scan_paths: str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    matches: list[dict[str, Any]] = []
    missing_paths: list[str] = []
    path_errors: list[str] = []
    for token in path_tokens(scan_paths):
        files, errors = candidate_files(root, token)
        path_errors.extend(f"{token}: {error}" for error in errors)
        if not files:
            if not errors:
                missing_paths.append(token)
            continue
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if phrase in line:
                    matches.append(
                        {
                            "path": display_path(root, path),
                            "line": line_no,
                            "line_sha256": hashlib.sha256(line.strip().encode("utf-8")).hexdigest(),
                        }
                    )
    return matches, missing_paths, path_errors


def validate(root: Path, task_plan_path: Path, progress_path: Path, strict_trigger: bool, check_template: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if is_template_path(progress_path) and not check_template:
        return {
            "status": "skipped",
            "reason": "raw templates are placeholders; use --check-template to validate template examples",
            "errors": [],
            "warnings": [],
            "row_count": 0,
            "checked": [],
        }
    progress_text = progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
    rows = extract_table(progress_text, "## Docs Fact Drift Check")
    real_rows = [
        row
        for row in rows
        if not is_placeholder(row_value(row, "implemented_capability", "capability", "claim"))
        or not is_placeholder(row_value(row, "stale_phrase", "future_work_phrase", "phrase"))
    ]

    if strict_trigger and not rows:
        warnings.append("strict trigger found no Docs Fact Drift Check rows; this is allowed unless the task updates documented future-work capabilities")

    checked: list[dict[str, Any]] = []
    for index, row in enumerate(real_rows, start=1):
        capability = row_value(row, "implemented_capability", "capability", "claim")
        phrase = row_value(row, "stale_phrase", "future_work_phrase", "phrase")
        scan_paths = row_value(row, "scan_paths", "paths", "checked_paths")
        disposition = row_value(row, "disposition", "status").lower()
        evidence = row_value(row, "evidence", "implemented_evidence", "source")

        item: dict[str, Any] = {
            "row": index,
            "implemented_capability": capability,
            "stale_phrase": phrase,
            "scan_paths": scan_paths,
            "disposition": disposition,
            "matches": [],
            "missing_paths": [],
            "path_errors": [],
        }
        checked.append(item)

        if disposition in SKIP_DISPOSITIONS:
            if not is_placeholder(scan_paths):
                path_errors = scan_path_policy_errors(root, scan_paths)
                item["path_errors"] = path_errors
                for path_error in path_errors:
                    errors.append(f"row {index}: scan path is not allowed: {path_error}")
            if disposition in EVIDENCE_REQUIRED_SKIP_DISPOSITIONS and is_placeholder(evidence):
                errors.append(f"row {index}: disposition {disposition} requires non-placeholder evidence / reason")
            continue
        if is_placeholder(capability):
            errors.append(f"row {index}: implemented capability is required")
        if is_placeholder(phrase):
            errors.append(f"row {index}: stale phrase / future-work phrase is required")
        if is_placeholder(scan_paths):
            errors.append(f"row {index}: scan paths are required")
        if is_placeholder(evidence):
            warnings.append(f"row {index}: implemented evidence is missing; validator can only check stale phrase presence")
        if is_placeholder(phrase) or is_placeholder(scan_paths):
            continue

        matches, missing_paths, path_errors = find_phrase(root, phrase, scan_paths)
        item["matches"] = matches
        item["missing_paths"] = missing_paths
        item["path_errors"] = path_errors
        for path_error in path_errors:
            errors.append(f"row {index}: scan path is not allowed: {path_error}")
        for missing in missing_paths:
            errors.append(f"row {index}: scan path matched no files: {missing}")
        if matches:
            first = matches[0]
            errors.append(
                f"row {index}: future work phrase remains after implementation: {phrase!r} at {first['path']}:{first['line']}"
            )

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "row_count": len(real_rows),
        "checked": checked,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate explicit docs/tests future-work fact drift rows.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan path. Reserved for future trigger checks.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--strict-trigger", action="store_true", help="Warn when the task omits Docs Fact Drift Check rows.")
    parser.add_argument("--check-template", action="store_true", help="Validate raw templates intentionally.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    task_plan = Path(args.task_plan)
    progress = Path(args.progress)
    if not task_plan.is_absolute():
        task_plan = root / task_plan
    if not progress.is_absolute():
        progress = root / progress
    payload = validate(root, task_plan, progress, args.strict_trigger, args.check_template)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        for warning in payload.get("warnings", []):
            print(f"warning: {warning}")
        for error in payload.get("errors", []):
            print(f"error: {error}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
