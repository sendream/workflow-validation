#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import current_task_snapshot as task_snapshot
import workflow_routing as wr
from markdown_document import section_text as markdown_section_text, without_fenced_blocks
from validator_result import run_json_validator


STALE_PLAN_PATTERNS = [
    r"\bdo not start coding\b",
    r"\bdo not implement\b",
    r"\bread-only\s*/\s*no-code\b",
    r"\bread-only\s+task\b",
    r"\bno-code\s+task\b",
    r"\bhealth-check scaffold\b",
    r"不开始编码",
    r"不启动编码",
    r"只读任务",
    r"不改代码",
    r"健康检查",
]

IMPLEMENTATION_PROGRESS_PATTERNS = [
    r"\bimplemented\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bapi\b",
    r"\bmigration\b",
    r"\bpytest\b",
    r"\btests?\b",
    r"\bsmoke\b",
    r"已实现",
    r"后端",
    r"前端",
    r"测试",
    r"迁移",
]

SCRIPT_DIR = Path(__file__).resolve().parent
CHILD_VALIDATOR_TIMEOUT_SECONDS = 30


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_text(markdown_text: str, heading: str) -> str:
    return markdown_section_text(markdown_text, heading)


def risk_tier(task_plan_text: str) -> str:
    return wr.risk_tier_or_unknown(task_plan_text)


def contains_any(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def extract_active_task_id(markdown_text: str, source_name: str) -> str | None:
    return task_snapshot.extract_active_task_id(markdown_text, source_name)


def validate_active_task_ids(task_plan_text: str, progress_text: str, findings_text: str | None, strict_required: bool) -> dict[str, Any]:
    ids = {
        "task_plan": extract_active_task_id(task_plan_text, "task_plan"),
        "progress": extract_active_task_id(progress_text, "progress"),
    }
    if findings_text is not None:
        ids["findings"] = extract_active_task_id(findings_text, "findings")

    present = {name: value for name, value in ids.items() if value}
    missing = [name for name, value in ids.items() if not value]
    unique = sorted(set(present.values()))
    errors: list[str] = []
    if strict_required and missing:
        errors.append("active task id is missing from: " + ", ".join(missing))
    if len(unique) > 1:
        errors.append("active task id mismatch across three files: " + ", ".join(f"{name}={value}" for name, value in present.items()))
    return {
        "ids": ids,
        "missing": missing,
        "unique": unique,
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def validate(
    root: Path,
    task_plan_path: Path,
    progress_path: Path,
    findings_path: Path | None = None,
    check_template: bool = False,
    require_existing_artifacts: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if is_template_path(task_plan_path) and not check_template:
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "risk_tier": "unknown",
            "checks": {},
        }

    if not task_plan_path.is_file():
        return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": [], "checks": {}}
    if not progress_path.is_file():
        return {"status": "fail", "errors": [f"progress file not found: {progress_path}"], "warnings": [], "checks": {}}

    task_plan_text = read_text(task_plan_path)
    progress_text = read_text(progress_path)
    findings_text: str | None = None
    if findings_path is not None and findings_path.is_file():
        findings_text = read_text(findings_path)
    tier = risk_tier(task_plan_text)
    strict_required = tier in {"high", "release"}
    if strict_required and findings_path is not None and not findings_path.is_file():
        errors.append(f"findings file not found for {tier} active task: {findings_path}")

    standard_state_paths = (
        task_plan_path == root / "task_plan.md"
        and progress_path == root / "progress.md"
        and (findings_path is None or findings_path == root / "findings.md")
    )
    if standard_state_paths:
        snapshot = task_snapshot.load_current_task_snapshot(root)
        checks["current_task_snapshot"] = asdict(snapshot)

    scripts_dir = root / ".agents" / "scripts"
    # Normal project runs use root/.agents/scripts. Starter-pack maintenance can
    # invoke this script against root-level task files before those scripts exist
    # at the repository root, so fall back to the script's own directory.
    if not (scripts_dir / "validate-traceability.py").is_file() and (SCRIPT_DIR / "validate-traceability.py").is_file():
        scripts_dir = SCRIPT_DIR
    validators = {
        "traceability": [
            sys.executable,
            str(scripts_dir / "validate-traceability.py"),
            "--root",
            str(root),
            "--task-plan",
            str(task_plan_path),
            "--progress",
            str(progress_path),
            "--strict-trigger",
            "--format",
            "json",
        ],
        "evidence_waivers": [
            sys.executable,
            str(scripts_dir / "validate-evidence-waivers.py"),
            "--root",
            str(root),
            "--task-plan",
            str(task_plan_path),
            "--progress",
            str(progress_path),
            "--strict-trigger",
            "--format",
            "json",
        ],
        "reviewer_assessment": [
            sys.executable,
            str(scripts_dir / "validate-reviewer-assessment.py"),
            "--root",
            str(root),
            "--task-plan",
            str(task_plan_path),
            "--progress",
            str(progress_path),
            "--strict-trigger",
            "--format",
            "json",
        ],
        "review_authorization": [
            sys.executable,
            str(scripts_dir / "validate-review-authorization.py"),
            "--root",
            str(root),
            "--task-plan",
            str(task_plan_path),
            "--progress",
            str(progress_path),
            "--strict-trigger",
            "--format",
            "json",
        ],
    }
    if require_existing_artifacts:
        evidence_command = validators["evidence_waivers"]
        evidence_command.insert(evidence_command.index("--format"), "--require-existing-artifacts")

    if strict_required:
        active_task_check = validate_active_task_ids(task_plan_text, progress_text, findings_text, strict_required)
        checks["active_task_id"] = active_task_check
        errors.extend(active_task_check["errors"])
        for name, command in validators.items():
            if not Path(command[1]).is_file():
                errors.append(f"{name} validator is missing: {command[1]}")
                continue
            result = run_json_validator(
                name,
                command,
                root,
                timeout=CHILD_VALIDATOR_TIMEOUT_SECONDS,
            )
            checks[name] = {
                "status": result.status,
                "returncode": result.returncode,
                "details": result.json if result.json is not None else result.stdout,
                "timed_out": result.timed_out,
                "parse_error": result.parse_error,
            }
            if result.status != "pass":
                errors.append(f"{name} validator failed; active high/release task needs migration or explicit waiver")
    else:
        warnings.append("risk tier is not high/release; strict active-task migration checks are not required")

    stale_hits = contains_any(without_fenced_blocks(task_plan_text), STALE_PLAN_PATTERNS)
    implementation_hits = contains_any(without_fenced_blocks(progress_text), IMPLEMENTATION_PROGRESS_PATTERNS)
    checks["phase_drift"] = {
        "stale_plan_patterns": stale_hits,
        "implementation_progress_patterns": implementation_hits[:8],
    }
    if stale_hits and implementation_hits:
        errors.append(
            "possible phase drift: task_plan still contains read-only/no-code constraints while progress shows implementation or tests"
        )

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "risk_tier": tier,
        "strict_required": strict_required,
        "checks": checks,
    }


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"risk_tier: {payload.get('risk_tier', 'unknown')}")
    print(f"strict_required: {str(payload.get('strict_required', False)).lower()}")
    if payload.get("warnings"):
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    if payload.get("errors"):
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")
    checks = payload.get("checks") or {}
    if checks:
        print("checks:")
        for name, check in checks.items():
            if isinstance(check, dict) and "status" in check:
                print(f"- {name}: {check['status']}")
            else:
                print(f"- {name}: recorded")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate that active task files were migrated after workflow gate updates.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan markdown file.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--findings", default="findings.md", help="Findings markdown file used for active task id consistency.")
    parser.add_argument("--check-template", action="store_true", help="Validate raw templates intentionally.")
    parser.add_argument("--require-existing-artifacts", action="store_true", help="Require referenced evidence artifacts through the owned evidence validator.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    task_plan_path = Path(args.task_plan)
    if not task_plan_path.is_absolute():
        task_plan_path = root / task_plan_path
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path
    findings_path = Path(args.findings) if args.findings else None
    if findings_path is not None and not findings_path.is_absolute():
        findings_path = root / findings_path

    payload = validate(
        root,
        task_plan_path,
        progress_path,
        findings_path=findings_path,
        check_template=args.check_template,
        require_existing_artifacts=args.require_existing_artifacts,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
