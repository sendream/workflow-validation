#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

import markdown_table as md
import workflow_routing as wr


VALID_STATUSES = {"completed", "deferred", "blocked"}
VALID_TASK_PATHS = {
    "fast path",
    "complex-task path",
    "focused verification",
    "full complex path",
    "release gate",
}
REQUIRED_ROOT_FILES = ("task_plan.md", "findings.md", "progress.md")
MANIFEST_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/manifest\.json\b")


def clean(value: str) -> str:
    return md.clean_cell(value)


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def section_text(markdown_text: str, heading: str) -> str:
    return "\n".join(wr.extract_section(markdown_text, heading)).strip()


def table_rows(markdown_text: str, heading: str) -> list[dict[str, str]]:
    section = section_text(markdown_text, heading)
    rows: list[dict[str, str]] = []
    for table in md.parse_markdown_tables(section, strict=False):
        headers = [normalize_key(header) for header in table.headers]
        for cells in table.rows:
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
    return rows


def root_file_texts(root: Path) -> tuple[dict[str, str], list[str]]:
    texts: dict[str, str] = {}
    errors: list[str] = []
    for filename in REQUIRED_ROOT_FILES:
        path = root / filename
        if not path.is_file():
            errors.append(f"missing root {filename}")
            continue
        texts[filename] = path.read_text(encoding="utf-8", errors="replace")
    return texts, errors


def first_nonempty(values: list[str], default: str) -> str:
    for value in values:
        cleaned = clean(value)
        if cleaned:
            return cleaned
    return default


def extract_acceptance_ids(task_plan_text: str) -> str:
    ids: list[str] = []
    for row in table_rows(task_plan_text, "Verification Matrix"):
        raw = row.get("acceptance___risk", "") or row.get("acceptance_risk", "") or row.get("acceptance", "")
        value = clean(raw)
        if value and value.lower() not in {"none", "not-needed", "pending", "待填写"}:
            ids.append(value)
    return ", ".join(dict.fromkeys(ids)) if ids else "none"


def extract_evidence_manifests(*texts: str) -> str:
    manifests: list[str] = []
    for text in texts:
        manifests.extend(MANIFEST_RE.findall(text))
    unique = list(dict.fromkeys(manifests))
    return ", ".join(unique) if unique else "none"


def extract_knowledge_promotion(findings_text: str) -> str:
    decisions: list[str] = []
    for row in table_rows(findings_text, "Knowledge Promotion"):
        decision = clean(row.get("decision", "")).lower()
        if decision in {"promote", "defer", "none", "not-needed", "already-promoted"}:
            if decision == "not-needed":
                decision = "none"
            decisions.append(decision)
    if not decisions:
        return "none"
    if "promote" in decisions:
        return "promote"
    if "defer" in decisions:
        return "defer"
    if "already-promoted" in decisions:
        return "already-promoted"
    return "none"


def extract_waivers(progress_text: str) -> str:
    rows = table_rows(progress_text, "Verification Waivers")
    concrete: list[str] = []
    for row in rows:
        check = clean(row.get("check", ""))
        reason = clean(row.get("reason", ""))
        if check.lower() in {"none", "not-needed", ""} and reason.lower() in {"none", "not-needed", ""}:
            continue
        if check and check.lower() not in {"none", "not-needed", "待填写"}:
            concrete.append(check)
    return ", ".join(dict.fromkeys(concrete)) if concrete else "none"


def extract_summary(progress_text: str) -> str:
    for row in table_rows(progress_text, "Current Status"):
        item = normalize_key(row.get("item", "") or row.get("field", "") or row.get("key", ""))
        if item == "summary":
            value = clean(row.get("value", ""))
            if value:
                return value
    return "Completed task archived from root three files."


def extract_next_action(progress_text: str) -> str:
    for row in table_rows(progress_text, "Current Status"):
        item = normalize_key(row.get("item", "") or row.get("field", "") or row.get("key", ""))
        if item == "next_action":
            value = clean(row.get("value", ""))
            if value:
                return value
    match = re.search(r"(?im)^\s*[-*]\s*Next Action\s*[:：]\s*(.+?)\s*$", progress_text)
    if match:
        return clean(match.group(1))
    return "none"


def extract_changed_modules(progress_text: str) -> str:
    values: list[str] = []
    for row in table_rows(progress_text, "Changed Files Manifest"):
        path = clean(row.get("path", ""))
        if path and path.lower() not in {"待填写", "none", "not-needed"}:
            values.append(path)
    return ", ".join(values[:12]) if values else "root three files and recorded task artifacts"


def summary_markdown(
    *,
    task_id: str,
    status: str,
    task_path: str,
    risk_tier: str,
    impact_scope: str,
    completed_at: str,
    changed_modules: str,
    acceptance_ids: str,
    evidence_manifests: str,
    waivers: str,
    knowledge_promotion: str,
    next_action: str,
    summary: str,
) -> str:
    return f"""# Task Archive Summary

> Reference-only archive. Do not treat this summary as current task instructions.

| field | value |
|---|---|
| archive_schema_version | 1 |
| task_id | {task_id} |
| status | {status} |
| task_path | {task_path} |
| risk_tier | {risk_tier} |
| impact_scope | {impact_scope} |
| completed_at | {completed_at} |
| changed_modules | {changed_modules} |
| acceptance_or_scenario_ids | {acceptance_ids} |
| evidence_manifests | {evidence_manifests} |
| waivers | {waivers} |
| knowledge_promotion | {knowledge_promotion} |
| next_task_or_follow_up | {next_action} |

## Summary

{summary}

## Key Decisions

- Archived the completed root three-file task as a reference-only historical record.
- Current task state remains the root three files until they are explicitly cleared or replaced.

## Evidence Index

- Evidence manifests: {evidence_manifests}

## Knowledge Promotion

{knowledge_promotion}

## Boundaries

- Reference-only archive; not active task state.
- Raw logs, screenshots, traces, HAR files, dumps, dependency caches, and generated release artifacts are intentionally not copied.
"""


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    root = Path(args.root).resolve()
    texts, errors = root_file_texts(root)
    if errors:
        return {"status": "fail", "errors": errors, "warnings": [], "root": str(root)}, errors, texts

    status = clean(args.status).lower()
    if status not in VALID_STATUSES:
        errors.append(f"status must be one of {sorted(VALID_STATUSES)}, not {args.status}")

    risk_tier = clean(args.risk_tier or wr.extract_risk_tier(texts["task_plan.md"]) or "")
    if risk_tier not in wr.VALID_RISK_TIERS:
        errors.append("risk tier must be provided in task_plan.md or --risk-tier")

    impact_scope = clean(args.impact_scope or wr.extract_impact_scope(texts["task_plan.md"]) or "")
    if impact_scope not in wr.VALID_IMPACT_SCOPES:
        errors.append("impact scope must be provided in task_plan.md or --impact-scope")

    task_path = clean(args.task_path)
    if task_path not in VALID_TASK_PATHS:
        errors.append(f"task path must be one of {sorted(VALID_TASK_PATHS)}, not {task_path}")

    task_id = clean(args.task_id)
    if not re.fullmatch(r"[0-9]{8}-[A-Za-z0-9][A-Za-z0-9._-]{1,80}", task_id):
        errors.append("task-id must look like YYYYMMDD-short-slug")

    archive_dir = root / ".agents" / "tasks" / task_id
    if archive_dir.exists() and not args.force:
        errors.append(f"archive already exists: {archive_dir}")

    summary_text = ""
    if not errors:
        summary_text = summary_markdown(
            task_id=task_id,
            status=status,
            task_path=task_path,
            risk_tier=risk_tier,
            impact_scope=impact_scope,
            completed_at=clean(args.completed_at),
            changed_modules=extract_changed_modules(texts["progress.md"]),
            acceptance_ids=extract_acceptance_ids(texts["task_plan.md"]),
            evidence_manifests=extract_evidence_manifests(*texts.values()),
            waivers=extract_waivers(texts["progress.md"]),
            knowledge_promotion=extract_knowledge_promotion(texts["findings.md"]),
            next_action=extract_next_action(texts["progress.md"]),
            summary=extract_summary(texts["progress.md"]),
        )

    payload = {
        "status": "fail" if errors else "pass",
        "mode": "apply" if args.apply else "dry-run",
        "root": str(root),
        "archive_dir": str(archive_dir.relative_to(root)),
        "writes": [] if not args.apply else [str(Path(".agents/tasks") / task_id / name) for name in ("summary.md", *REQUIRED_ROOT_FILES)],
        "errors": errors,
        "warnings": [],
        "boundaries": {
            "reference_only": True,
            "authoritative_current_state": False,
            "current_state_source": "root three files remain authoritative until explicitly cleared or replaced",
            "derived_from_root_three_files": True,
            "raw_logs_read": False,
            "clears_root_three_files": False,
        },
    }
    if summary_text:
        payload["_summary_text"] = summary_text
        payload["summary_preview"] = summary_text if not args.apply else "written"
    return payload, errors, texts


def apply_archive(root: Path, task_id: str, summary_text: str, force: bool) -> None:
    archive_dir = root / ".agents" / "tasks" / task_id
    if archive_dir.exists() and force:
        shutil.rmtree(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=False)
    (archive_dir / "summary.md").write_text(summary_text, encoding="utf-8")
    for filename in REQUIRED_ROOT_FILES:
        shutil.copy2(root / filename, archive_dir / filename)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a summary-first completed task archive from root three files.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-id", required=True, help="Archive id, e.g. 20260629-feature-closeout.")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), default="completed")
    parser.add_argument("--task-path", choices=sorted(VALID_TASK_PATHS), default="complex-task path")
    parser.add_argument("--risk-tier", choices=wr.VALID_RISK_TIERS)
    parser.add_argument("--impact-scope", choices=wr.VALID_IMPACT_SCOPES)
    parser.add_argument("--completed-at", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true", help="Preview the archive without writing. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Write the archive. Without this, dry-run only.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing archive directory.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"mode: {payload['mode']}")
    print(f"archive_dir: {payload['archive_dir']}")
    for error in payload.get("errors", []):
        print(f"error: {error}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")
    if payload.get("summary_preview") and payload["mode"] == "dry-run":
        print("\n--- summary preview ---")
        print(payload["summary_preview"])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.apply and args.dry_run:
        print("error: use either --dry-run or --apply, not both", file=sys.stderr)
        return 2
    payload, errors, texts = build_payload(args)
    root = Path(args.root).resolve()
    if not errors and args.apply:
        apply_archive(
            root,
            clean(args.task_id),
            str(payload.pop("_summary_text")),
            args.force,
        )
    else:
        payload.pop("_summary_text", None)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
