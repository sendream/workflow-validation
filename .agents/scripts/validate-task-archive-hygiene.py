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


REQUIRED_FILES = ("summary.md", "task_plan.md", "findings.md", "progress.md")
REQUIRED_SUMMARY_FIELDS = {
    "archive_schema_version",
    "task_id",
    "status",
    "task_path",
    "risk_tier",
    "impact_scope",
    "completed_at",
    "changed_modules",
    "acceptance_or_scenario_ids",
    "evidence_manifests",
    "waivers",
    "knowledge_promotion",
    "next_task_or_follow_up",
}
REQUIRED_SUMMARY_SECTIONS = (
    "## Summary",
    "## Key Decisions",
    "## Evidence Index",
    "## Knowledge Promotion",
    "## Boundaries",
)
VALID_ARCHIVE_STATUSES = {"completed", "deferred", "blocked"}
VALID_RISK_TIERS = {"low", "standard", "high", "release"}
VALID_TASK_PATHS = {
    "fast path",
    "complex-task path",
    "focused verification",
    "full complex path",
    "release gate",
}
PLACEHOLDERS = {"", "待填写", "pending", "missing", "required", "not-recorded", "unknown"}
NONE_LIKE = {"none", "not-needed", "not needed", "n/a", "na"}
RUN_MANIFEST_RE = re.compile(r"^`?\.agent-state/runs/[A-Za-z0-9._-]+/manifest\.json`?$")
RUN_BARE_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/?(?:\s|$|`)")
RUN_REPORT_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/(?!manifest\.json\b)[^\s|`]+\.json\b")
FORBIDDEN_SUFFIXES = {
    ".log",
    ".har",
    ".trace",
    ".zip",
    ".jar",
    ".war",
    ".tar",
    ".tgz",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".webm",
    ".mp4",
    ".db",
    ".sqlite",
    ".dump",
    ".pem",
    ".key",
}
FORBIDDEN_NAME_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)node_modules(/|$)"),
    re.compile(r"(^|/)\.venv(/|$)"),
    re.compile(r"(^|/)venv(/|$)"),
    re.compile(r"(^|/)dist(/|$)"),
    re.compile(r"(^|/)build(/|$)"),
    re.compile(r"(^|/)outputs?(/|$)"),
    re.compile(r"(^|/)artifacts?(/|$)"),
    re.compile(r"(^|/)cache(/|$)"),
)
MAX_ARCHIVE_FILE_BYTES = 512 * 1024


def clean(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def is_placeholder(value: str) -> bool:
    normalized = clean(value).lower()
    return normalized in PLACEHOLDERS or "待填写" in normalized


def summary_fields(summary_text: str, *, strict: bool = False) -> dict[str, str]:
    fields: dict[str, str] = {}
    for row in md_doc.table_dict_rows(
        summary_text,
        strict=strict,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    ):
        field = row.get("field") or row.get("item") or row.get("key")
        value = row.get("value", "")
        if field:
            fields[normalize_key(field)] = value
    return fields


def has_heading(markdown_text: str, heading: str) -> bool:
    return any(line.strip() == heading for line in markdown_text.splitlines())


def section_body(markdown_text: str, heading: str) -> str:
    lines = markdown_text.splitlines()
    in_section = False
    body: list[str] = []
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)
    return "\n".join(body).strip()


def meaningful_section(markdown_text: str, heading: str) -> bool:
    body = section_body(markdown_text, heading)
    if not body:
        return False
    normalized = re.sub(r"[\s`>*_-]+", "", body).lower()
    if not normalized:
        return False
    return normalized not in {"none", "notneeded", "待填写", "pending", "missing", "required", "na"}


def evidence_manifest_values(value: str) -> list[str]:
    cleaned = clean(value)
    if not cleaned:
        return []
    parts = re.split(r"[,;\n]+", cleaned)
    values: list[str] = []
    for part in parts:
        token = clean(part)
        if token:
            values.append(token)
    return values


def validate_evidence_manifest_field(archive_name: str, value: str, strict: bool, errors: list[str], warnings: list[str]) -> None:
    cleaned = clean(value)
    lowered = cleaned.lower()
    if not cleaned or lowered in PLACEHOLDERS or lowered in NONE_LIKE:
        return
    if "/tmp/" in lowered and not any(marker in lowered for marker in ("local-only", "not persisted", "not-persisted")):
        severity_append(
            errors,
            warnings,
            strict,
            f"{archive_name}: evidence_manifests references /tmp without local-only / not persisted marker",
        )
    for item in evidence_manifest_values(cleaned):
        item_lower = item.lower()
        if item_lower in NONE_LIKE:
            continue
        if RUN_MANIFEST_RE.fullmatch(item):
            continue
        if RUN_REPORT_RE.search(item) or RUN_BARE_RE.search(item):
            severity_append(
                errors,
                warnings,
                strict,
                f"{archive_name}: evidence_manifests must reference .agent-state/runs/<run_id>/manifest.json, not report JSON or bare run directory: {item}",
            )
        elif ".agent-state/runs/" in item:
            severity_append(
                errors,
                warnings,
                strict,
                f"{archive_name}: evidence_manifests contains non-manifest run evidence path: {item}",
            )
        else:
            severity_append(
                errors,
                warnings,
                strict,
                f"{archive_name}: evidence_manifests entries must be none or .agent-state/runs/<run_id>/manifest.json, not {item}",
            )


def is_formal_archive_path(root: Path, archive: Path) -> bool:
    tasks_root = root / ".agents" / "tasks"
    try:
        archive.resolve().relative_to(tasks_root.resolve())
    except ValueError:
        return False
    return archive.name != "README.md" and not archive.name.startswith(".")


def is_archive_ready_path(root: Path, archive: Path) -> bool:
    ready_root = root / ".agent-state" / "tasks" / "archive-ready"
    try:
        archive.resolve().relative_to(ready_root.resolve())
        return True
    except ValueError:
        return False


def strict_for_archive(explicit_archive: bool, strict_new: bool, legacy_warn: bool) -> bool:
    if strict_new:
        return True
    if explicit_archive and not legacy_warn:
        return True
    return False


def severity_append(errors: list[str], warnings: list[str], strict: bool, message: str) -> None:
    if strict:
        errors.append(message)
    else:
        warnings.append(message)


def forbidden_file_reason(root: Path, path: Path) -> str | None:
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    lower = rel.lower()
    if path.name in REQUIRED_FILES:
        return None
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"forbidden archive artifact type: {rel}"
    if any(pattern.search(lower) for pattern in FORBIDDEN_NAME_PATTERNS):
        return f"forbidden archive runtime/artifact path: {rel}"
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > MAX_ARCHIVE_FILE_BYTES:
        return f"archive file is too large for summary-first storage: {rel} ({size} bytes)"
    return None


def validate_archive(root: Path, archive: Path, strict: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    archive = archive.resolve()

    if is_archive_ready_path(root, archive):
        severity_append(
            errors,
            warnings,
            strict,
            f"{archive}: .agent-state/tasks/archive-ready is staging, not a formal archive",
        )
    elif not is_formal_archive_path(root, archive):
        errors.append(f"{archive}: archive must live under .agents/tasks/<task-id>")

    if not archive.is_dir():
        errors.append(f"{archive}: archive directory not found")
        return {"archive": str(archive), "status": "fail", "errors": errors, "warnings": warnings}

    for filename in REQUIRED_FILES:
        if not (archive / filename).is_file():
            severity_append(errors, warnings, strict, f"{archive.name}: missing {filename}")

    summary_path = archive / "summary.md"
    summary_text = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    if summary_text:
        if "reference-only" not in summary_text.lower():
            severity_append(errors, warnings, strict, f"{archive.name}: summary.md must include reference-only marker")
        for heading in REQUIRED_SUMMARY_SECTIONS:
            if not has_heading(summary_text, heading):
                severity_append(errors, warnings, strict, f"{archive.name}: summary.md missing required section {heading}")
            elif heading in {"## Summary", "## Evidence Index", "## Boundaries"} and not meaningful_section(summary_text, heading):
                severity_append(errors, warnings, strict, f"{archive.name}: summary.md section {heading} must contain non-placeholder content")
        try:
            fields = summary_fields(summary_text, strict=True)
        except md_table.MarkdownTableError as exc:
            severity_append(errors, warnings, strict, f"{archive.name}: summary.md table is malformed: {exc}")
            fields = {} if strict else summary_fields(summary_text, strict=False)
        missing_fields = sorted(field for field in REQUIRED_SUMMARY_FIELDS if is_placeholder(fields.get(field, "")))
        for field in missing_fields:
            severity_append(errors, warnings, strict, f"{archive.name}: summary.md missing required field {field}")
        schema_version = clean(fields.get("archive_schema_version", ""))
        if schema_version and not is_placeholder(schema_version) and schema_version != "1":
            severity_append(errors, warnings, strict, f"{archive.name}: archive_schema_version must be 1")
        archive_status = clean(fields.get("status", "")).lower()
        if archive_status and not is_placeholder(archive_status) and archive_status not in VALID_ARCHIVE_STATUSES:
            severity_append(errors, warnings, strict, f"{archive.name}: status must be completed/deferred/blocked, not {archive_status}")
        risk_tier = clean(fields.get("risk_tier", "")).lower()
        if risk_tier and not is_placeholder(risk_tier) and risk_tier not in VALID_RISK_TIERS:
            severity_append(errors, warnings, strict, f"{archive.name}: risk_tier must be low/standard/high/release, not {risk_tier}")
        task_path = clean(fields.get("task_path", "")).lower()
        if task_path and not is_placeholder(task_path) and task_path not in VALID_TASK_PATHS:
            warnings.append(f"{archive.name}: task_path is non-standard: {task_path}")
        evidence_manifests = clean(fields.get("evidence_manifests", "")).lower()
        validate_evidence_manifest_field(archive.name, evidence_manifests, strict, errors, warnings)
        knowledge_promotion = clean(fields.get("knowledge_promotion", "")).lower()
        if knowledge_promotion and not is_placeholder(knowledge_promotion) and knowledge_promotion not in {"promote", "defer", "none", "already-promoted"}:
            severity_append(
                errors,
                warnings,
                strict,
                f"{archive.name}: knowledge_promotion must be promote/defer/none/already-promoted, not {knowledge_promotion}",
            )

    progress_path = archive / "progress.md"
    if progress_path.is_file():
        progress_text = progress_path.read_text(encoding="utf-8", errors="replace").lower()
        active_markers = (
            "三文件状态：active",
            "三文件状态: active",
            "status: active",
            "status：active",
            "current status\n- status: active",
        )
        if any(marker in progress_text for marker in active_markers):
            severity_append(errors, warnings, strict, f"{archive.name}: archived progress.md still claims active status")

    for path in archive.rglob("*"):
        if not path.is_file():
            continue
        reason = forbidden_file_reason(archive, path)
        if reason:
            severity_append(errors, warnings, strict, f"{archive.name}: {reason}")

    return {
        "archive": archive.name,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
    }


def archive_candidates(root: Path) -> list[Path]:
    tasks_root = root / ".agents" / "tasks"
    if not tasks_root.is_dir():
        return []
    return sorted(path for path in tasks_root.iterdir() if path.is_dir() and not path.name.startswith("."))


def validate(
    root: Path,
    archives: list[Path],
    all_archives: bool,
    strict_new: bool,
    legacy_warn: bool,
) -> dict[str, Any]:
    explicit_archive = bool(archives)
    targets = archives or (archive_candidates(root) if all_archives else [])
    if not targets:
        return {
            "status": "fail",
            "errors": ["no archive target provided; use --archive or --all-archives"],
            "warnings": [],
            "archives": [],
        }

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    strict = strict_for_archive(explicit_archive, strict_new, legacy_warn)
    for archive in targets:
        archive_path = archive if archive.is_absolute() else root / archive
        result = validate_archive(root, archive_path, strict)
        results.append(result)
        errors.extend(result["errors"])
        warnings.extend(result["warnings"])

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "archive_count": len(results),
        "strict": strict,
        "archives": results,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate completed task archive hygiene without reading raw history by default.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--archive", action="append", default=[], help="Archive directory to validate. May be repeated.")
    parser.add_argument("--all-archives", action="store_true", help="Validate every .agents/tasks/<task-id> directory.")
    parser.add_argument("--strict-new", action="store_true", help="Fail missing summary/schema/content issues for new archives.")
    parser.add_argument("--legacy-warn", action="store_true", help="Warn instead of failing legacy archive hygiene gaps.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"archives: {payload.get('archive_count', 0)}")
    for error in payload.get("errors", []):
        print(f"error: {error}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    archives = [Path(item) for item in args.archive]
    payload = validate(root, archives, args.all_archives, args.strict_new, args.legacy_warn)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
