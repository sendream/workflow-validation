#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc


REVIEW_TRIGGER_PATTERNS = [
    r"\breview\b",
    r"\baudit\b",
    r"\bevaluat(?:e|ion)\b",
    r"\binspect\b",
    r"\bcompliance\b",
    r"\bworkflow compliance\b",
    r"\bread-only\b",
    r"\bno-code\b",
    r"审查",
    r"评估",
    r"核查",
    r"复盘",
    r"只读",
    r"不改代码",
    r"是否符合",
    r"还原.*执行",
]

IMPLEMENTATION_PROGRESS_PATTERNS = [
    r"\bimplemented\b",
    r"\bpatched\b",
    r"\bmodified\b",
    r"\bcode changed\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bapi\b",
    r"\bmigration\b",
    r"\bpytest\b",
    r"\btests?\b",
    r"\bsmoke\b",
    r"\bdeploy(?:ed|ment)?\b",
    r"\bbuild\b",
    r"已实现",
    r"已修复",
    r"改代码",
    r"写入",
    r"后端",
    r"前端",
    r"接口",
    r"迁移",
    r"测试",
    r"部署",
    r"修复",
]

VALID_MODES = {"review-only", "plan-only", "report-write-only", "implementation-authorized", "not-needed"}
VALID_WRITE_AUTH = {"none", "report-only", "task", "session", "revoked", "not-needed"}
VALID_DISPOSITION = {"accepted-as-finding-only", "implementation-approved", "not-needed"}
VALID_TRANSITION = {"stay-readonly", "report-write-only", "ask-user", "implement-authorized", "not-needed"}
REPORT_ARTIFACT_EXTENSIONS = {".md", ".txt", ".json", ".html", ".pdf"}
REPORT_ARTIFACT_TERMS = ("report", "review", "audit", "assessment", "findings", "summary", "报告", "审查", "审核", "评估", "核查")

PLACEHOLDERS = {
    "",
    "none",
    "n/a",
    "na",
    "待填写",
    "optional",
    "todo",
    "tbd",
    "not-needed",
    "用户消息 / task instruction / not-needed",
}


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_section(markdown_text: str, heading: str) -> str:
    return md_doc.section_text(markdown_text, heading)


def remove_section(markdown_text: str, heading: str) -> str:
    return md_doc.remove_section(markdown_text, heading)


def selected_progress_evidence_text(markdown_text: str) -> str:
    headings = [
        "## Current Status",
        "## Completed",
        "## In Progress",
        "## Run Evidence",
        "## Validation",
        "## Changed Files Manifest",
        "## Diff-to-Plan",
        "## Handoff",
    ]
    return "\n\n".join(extract_section(markdown_text, heading) for heading in headings)


def selected_task_review_intent_text(markdown_text: str) -> str:
    # Keep review/audit intent detection out of workflow mechanics sections such as
    # Isolated Reviewer Assessment and stale archived task/contract sections; those
    # sections are normal implementation gates or historical task baggage. Current
    # review/audit intent must be visible in the active snapshot or explicit boundary.
    headings = [
        "## Active Task Snapshot",
        "## Review / Audit Boundary",
    ]
    return "\n\n".join(extract_section(markdown_text, heading) for heading in headings)


def parse_key_value_table(section: str) -> dict[str, str]:
    return md_doc.key_value_table(section)


def contains_any(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            hits.append(pattern)
    return hits


def placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().strip("`").lower()
    return normalized in PLACEHOLDERS or "待填写" in normalized


def normalize(value: str | None) -> str:
    return (value or "").strip().strip("`").lower()


def extract_path_tokens(value: str) -> list[str]:
    stripped = value.strip()
    backtick_tokens = re.findall(r"`([^`]+)`", stripped)
    if backtick_tokens:
        return [token.strip() for token in backtick_tokens if token.strip()]
    return [token.strip() for token in re.split(r"\s*(?:,|;|\band\b|和|、)\s*", stripped) if token.strip()]


def is_report_artifact_scope(value: str) -> bool:
    tokens = extract_path_tokens(value)
    if len(tokens) != 1:
        return False
    token = tokens[0].strip().strip("'\"")
    normalized = token.lower()
    if normalized in {".", "./", "repo", "repository", "root", "project", "all", "*"}:
        return False
    if any(ch in normalized for ch in "*?[]{}"):
        return False
    if normalized.endswith("/") or normalized.endswith("\\"):
        return False
    path = Path(token)
    if path.is_absolute():
        return False
    if path.suffix.lower() not in REPORT_ARTIFACT_EXTENSIONS:
        return False
    if any(part in {".git", ".codex", ".ssh"} for part in path.parts):
        return False
    semantic = normalized.replace("\\", "/")
    return any(term in semantic for term in REPORT_ARTIFACT_TERMS)


def validate(task_plan_path: Path, progress_path: Path, check_template: bool = False, strict_trigger: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if is_template_path(progress_path) and not check_template:
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "review_trigger_detected": False,
            "implementation_evidence_detected": False,
        }

    if not task_plan_path.is_file():
        return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": []}
    if not progress_path.is_file():
        return {"status": "fail", "errors": [f"progress file not found: {progress_path}"], "warnings": []}

    task_plan_text = read_text(task_plan_path)
    progress_text = read_text(progress_path)
    boundary_section = extract_section(progress_text, "## Review / Audit Boundary")
    progress_without_boundary = remove_section(progress_text, "## Review / Audit Boundary")
    progress_evidence_text = selected_progress_evidence_text(progress_without_boundary)

    review_detection_text = "\n".join(
        [
            selected_task_review_intent_text(task_plan_text),
            boundary_section,
            extract_section(progress_text, "## Current Status"),
        ]
    )
    review_hits = contains_any(review_detection_text, REVIEW_TRIGGER_PATTERNS)
    implementation_hits = contains_any(progress_evidence_text, IMPLEMENTATION_PROGRESS_PATTERNS)
    review_trigger_detected = bool(review_hits)
    implementation_evidence_detected = bool(implementation_hits)

    values = parse_key_value_table(boundary_section) if boundary_section else {}
    mode = normalize(values.get("mode"))
    write_authorization = normalize(values.get("write authorization"))
    authorization_source = values.get("authorization source", "")
    allowed_write_scope = values.get("allowed write scope", "")
    finding_policy = normalize(values.get("finding disposition policy"))
    transition_decision = normalize(values.get("transition decision"))

    if not boundary_section:
        if strict_trigger and review_trigger_detected and implementation_evidence_detected:
            errors.append("review/audit-like task shows implementation evidence but Review / Audit Boundary is missing")
        elif review_trigger_detected and implementation_evidence_detected:
            warnings.append("review/audit-like task shows implementation evidence; add Review / Audit Boundary for auditable authorization")
        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "warnings": warnings,
            "mode": "missing",
            "write_authorization": "missing",
            "review_trigger_detected": review_trigger_detected,
            "review_trigger_hits": review_hits[:8],
            "implementation_evidence_detected": implementation_evidence_detected,
            "implementation_hits": implementation_hits[:8],
        }

    if mode not in VALID_MODES:
        errors.append(f"invalid Review / Audit Boundary mode: {mode or '<empty>'}")
    if write_authorization not in VALID_WRITE_AUTH:
        errors.append(f"invalid Review / Audit Boundary write authorization: {write_authorization or '<empty>'}")
    if finding_policy not in VALID_DISPOSITION:
        errors.append(f"invalid Review / Audit Boundary finding disposition policy: {finding_policy or '<empty>'}")
    if transition_decision not in VALID_TRANSITION:
        errors.append(f"invalid Review / Audit Boundary transition decision: {transition_decision or '<empty>'}")

    if mode in {"review-only", "plan-only"}:
        if write_authorization not in {"none", "revoked", "not-needed"}:
            errors.append("review-only / plan-only mode cannot have task/session write authorization")
        if finding_policy == "implementation-approved":
            errors.append("review-only / plan-only mode cannot mark findings as implementation-approved")
        if transition_decision == "implement-authorized":
            errors.append("review-only / plan-only mode cannot transition to implement-authorized")
        if implementation_evidence_detected:
            errors.append("review-only / plan-only mode has implementation evidence; explicit implementation authorization is required")

    if mode == "report-write-only":
        if write_authorization != "report-only":
            errors.append("report-write-only mode requires Write authorization=report-only")
        if placeholder(authorization_source):
            errors.append("report-write-only mode requires a concrete Authorization source")
        if placeholder(allowed_write_scope):
            errors.append("report-write-only mode requires a concrete Allowed write scope for the report artifact")
        elif any(term in allowed_write_scope.lower() for term in ("task_plan.md", "progress.md", "findings.md", "src/", "app/", "backend/", "frontend/")):
            errors.append("report-write-only Allowed write scope must be limited to a report artifact, not三文件 or business/source paths")
        elif not is_report_artifact_scope(allowed_write_scope):
            errors.append("report-write-only Allowed write scope must name exactly one report artifact path")
        if finding_policy == "implementation-approved":
            errors.append("report-write-only mode cannot mark findings as implementation-approved")
        if transition_decision != "report-write-only":
            errors.append("report-write-only mode requires Transition decision=report-write-only")
        if implementation_evidence_detected:
            errors.append("report-write-only mode has implementation evidence; explicit implementation authorization is required")

    if mode == "implementation-authorized":
        if write_authorization not in {"task", "session"}:
            errors.append("implementation-authorized mode requires Write authorization=task or session")
        if placeholder(authorization_source):
            errors.append("implementation-authorized mode requires a concrete Authorization source")
        if placeholder(allowed_write_scope):
            errors.append("implementation-authorized mode requires a concrete Allowed write scope")
        if finding_policy != "implementation-approved":
            errors.append("implementation-authorized mode requires Finding disposition policy=implementation-approved")
        if transition_decision != "implement-authorized":
            errors.append("implementation-authorized mode requires Transition decision=implement-authorized")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "mode": mode or "missing",
        "write_authorization": write_authorization or "missing",
        "review_trigger_detected": review_trigger_detected,
        "review_trigger_hits": review_hits[:8],
        "implementation_evidence_detected": implementation_evidence_detected,
        "implementation_hits": implementation_hits[:8],
        "authorization_source": authorization_source,
        "allowed_write_scope": allowed_write_scope,
        "finding_disposition_policy": finding_policy,
        "transition_decision": transition_decision,
    }


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"mode: {payload.get('mode', 'missing')}")
    print(f"write_authorization: {payload.get('write_authorization', 'missing')}")
    print(f"review_trigger_detected: {str(payload.get('review_trigger_detected', False)).lower()}")
    print(f"implementation_evidence_detected: {str(payload.get('implementation_evidence_detected', False)).lower()}")
    if payload.get("warnings"):
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    if payload.get("errors"):
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate review/audit read-only boundary and implementation authorization.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan markdown file.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--strict-trigger", action="store_true", help="Fail if review/audit trigger plus implementation evidence has no boundary.")
    parser.add_argument("--check-template", action="store_true", help="Validate raw templates intentionally.")
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

    payload = validate(
        task_plan_path=task_plan_path,
        progress_path=progress_path,
        check_template=args.check_template,
        strict_trigger=args.strict_trigger,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
