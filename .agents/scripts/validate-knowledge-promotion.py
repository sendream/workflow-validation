#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc

import workflow_routing as wr


DECISIONS_REQUIRING_METADATA = {"promote", "defer", "already-promoted"}
PLACEHOLDER_OPTIONS = {"promote", "defer", "none", "not-needed", "already-promoted", "updated", "deferred", "candidate"}
VALID_DECISIONS = {"promote", "defer", "none", "not-needed", "already-promoted"}
VALID_RELATIONS = {"", "not-needed", "new", "confirms", "updates", "supersedes", "invalidates"}
KNOWN_REFERENCE_TARGETS = {
    "README.md": "README.md",
    "project-conventions.md": ".agents/references/project-conventions.md",
    "architecture-notes.md": ".agents/references/architecture-notes.md",
    "common-pitfalls.md": ".agents/references/common-pitfalls.md",
    "requirements-index.md": ".agents/references/requirements-index.md",
    "feature-index.md": ".agents/references/feature-index.md",
    "tooling-map.md": ".agents/references/tooling-map.md",
    "browser-regression.md": ".agents/references/browser-regression.md",
    "terminology.md": ".agents/references/terminology.md",
}
LANDING_MARKER_RE = re.compile(r"^(?:evidence|marker):[A-Za-z0-9._:-]+$")
RUN_EVIDENCE_MARKER_RE = re.compile(
    r"^\.agent-state/runs/[A-Za-z0-9._-]+/"
    r"(?:manifest\.json|summary\.md|[A-Za-z0-9._-]*(?:report|result|validation|evidence|marker)[A-Za-z0-9._-]*\.(?:json|md))$"
)
REFERENCE_PREFIXES = (".agents/references/", "starter-pack/project/.agents/references/")
README_TARGETS = {"README.md", "starter-pack/README.md"}
TRACKER_TERMS = (
    "due date",
    "deadline",
    "status flow",
    "issue owner",
    "backlog",
    "todo owner",
    "kanban",
    "sprint",
    "到期",
    "负责人",
    "状态流",
    "待办",
)
FORBIDDEN_FEEDBACK_TERMS = (
    "auto-generate",
    "auto generate",
    "generate eval",
    "create-now",
    "eval backlog",
    "next action",
    "owner",
    "due date",
    "deadline",
    "负责人",
    "截止",
)
FEEDBACK_HEADINGS = ("## Real Task Feedback Loop", "## Real Task Feedback Signals")
TRACE_INTAKE_HEADINGS = ("## Trace-to-Eval Intake",)
VALID_FEEDBACK_SIGNALS = {
    "not-needed",
    "workflow miss",
    "validator false-positive",
    "validator false-negative",
    "repeated waiver",
    "repeated failure signature",
    "high-value reviewer finding",
    "reviewer calibration gap",
    "evidence gap",
    "knowledge drift",
    "accepted-reviewer-finding",
    "repeated-defect",
    "verification-gap",
    "stale-knowledge",
    "workflow-friction",
    "tool-cost",
}
VALID_ATTRIBUTION_TYPES = {
    "not-needed",
    "knowledge-gap",
    "skill-defect",
    "execution-lapse",
    "validator-gap",
    "reviewer-gap",
    "tooling-gap",
    "environment-debt",
    "docs-drift",
    "external-change",
    "routing-gap",
    "template-gap",
}
VALID_FEEDBACK_DECISIONS = {
    "none",
    "eval-candidate",
    "knowledge-candidate",
    "metric-candidate",
    "validator-candidate",
    "candidate",
    "already-covered",
    "defer",
    "deferred",
}
VALID_FEEDBACK_TARGETS = {
    "not-needed",
    "behavior eval",
    "trajectory eval",
    "static-eval",
    "validator",
    "reference",
    "reviewer metrics",
    "knowledge-promotion",
    "local-skill",
    "template",
}
REWRITE_TARGETS = {"local-skill", "reference", "template", "knowledge-promotion"}
VALID_FEEDBACK_EPOCHS = {"legacy", "migration", "current", "not-needed"}
VALID_AUDIT_LENSES = {"active", "submitted", "archive", "not-needed"}
INVALID_UNKNOWN_TIMING_VALUES = {"unknown", "unclear", "not-known", "not known"}
FEEDBACK_COHORT_FIELDS = (
    "task_epoch",
    "audit_lens",
    "mechanism_id",
    "introduced_at",
    "workflow_synced_at",
    "applies_from",
    "source_baseline",
)
EVAL_CANDIDATE_TYPES = {
    "behavior eval",
    "trajectory eval",
    "static-eval",
    "behavior fixture",
    "trajectory fixture",
    "validator fixture",
    "live-eval-experiment",
}
VALID_SKILL_CANDIDATE_DECISIONS = {
    "none",
    "candidate",
    "update-needed",
    "recommend-create",
    "recommend-promote",
    "defer",
}
STRONG_SKILL_CANDIDATE_DECISIONS = {"update-needed", "recommend-create", "recommend-promote"}
VALID_SKILL_CANDIDATE_TYPES = {
    "new-skill-candidate",
    "skill-update-candidate",
    "starter-pack-promotion-candidate",
    "global-skill-candidate",
    "none",
}
STRICT_SIGNAL_HEADINGS = (
    "## Known-Bad Path",
    "## Environment Debt",
    "## Architecture Impact",
    "## Defect Records",
    "## Knowledge Promotion",
    "## Real Task Feedback Loop",
    "## Real Task Feedback Signals",
)


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("/", "_")


def is_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if not normalized or normalized in {"待填写", "none", "not-needed", "missing", "pending"} or "待填写" in normalized:
        return True
    if " / " in normalized:
        parts = [part.strip() for part in normalized.split("/")]
        return any(part in PLACEHOLDER_OPTIONS for part in parts)
    return False


def is_decision_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if normalized in {"none", "not-needed"}:
        return False
    return is_placeholder(value)


def row_reason(row: dict[str, str]) -> str:
    return row.get("reason___owner", "") or row.get("reason_owner", "") or row.get("reason", "")


def row_eval_guard(row: dict[str, str]) -> str:
    return (
        row.get("eval_guard", "")
        or row.get("eval___guard", "")
        or row.get("trigger_eval_guard", "")
        or row.get("trigger_eval___guard", "")
    )


def row_landing_evidence(row: dict[str, str]) -> str:
    return (
        row.get("landing_evidence", "")
        or row.get("landing___evidence", "")
        or row.get("reference_evidence", "")
        or row.get("reference___evidence", "")
    )


def has_eval_guard(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if is_placeholder(normalized):
        return False
    if normalized.startswith("already-covered:") or "already-covered" in normalized:
        return True
    return "positive" in normalized and "negative" in normalized and ("failure" in normalized or "oracle" in normalized)


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def extract_section(markdown_text: str, heading: str) -> list[str]:
    lines = markdown_text.splitlines()
    in_section = False
    section: list[str] = []
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            section.append(line)
    return section


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=False,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def extract_first_table(markdown_text: str, headings: tuple[str, ...]) -> tuple[str, list[dict[str, str]]]:
    for heading in headings:
        rows = extract_table(markdown_text, heading)
        if rows:
            return heading, rows
    return "", []


def has_workflow_trace_intake_claim(progress_text: str | None) -> bool:
    if not progress_text:
        return False
    for row in extract_table(progress_text, "## Workflow Trace"):
        step = clean_cell(row.get("step", "")).lower()
        status = clean_cell(row.get("status", "")).lower()
        if step == "trace_to_eval_intake" and status in {"candidate", "recorded"}:
            return True
    return False


def is_feedback_candidate(decision: str, target: str, candidate_eval_type: str = "") -> bool:
    if decision in {"", "none", "not-needed", "already-covered"}:
        return False
    if decision == "eval-candidate":
        return True
    if target in EVAL_CANDIDATE_TYPES:
        return True
    return candidate_eval_type in EVAL_CANDIDATE_TYPES


def validate_feedback_rows(
    rows: list[dict[str, str]],
    *,
    source_name: str,
    require_signal_enum: bool,
) -> tuple[list[str], int]:
    errors: list[str] = []
    checked_feedback = 0
    for row in rows:
        signal = clean_cell(row.get("signal", "")).lower()
        decision = clean_cell(row.get("decision", "") or row.get("disposition", "")).lower()
        target = clean_cell(row.get("target", "") or row.get("candidate_target", "")).lower()
        candidate_eval_type = clean_cell(row.get("candidate_eval_type", "")).lower()
        evidence = clean_cell(row.get("source_evidence", "") or row.get("source_trace___artifact", "") or row.get("evidence", ""))
        attribution = clean_cell(row.get("attribution_type", "") or row.get("attribution", "")).lower()
        if is_placeholder(signal) and is_placeholder(decision) and is_placeholder(target) and is_placeholder(candidate_eval_type):
            continue
        checked_feedback += 1
        if require_signal_enum and signal and not is_placeholder(signal) and signal not in VALID_FEEDBACK_SIGNALS:
            errors.append(f"{source_name}: signal must be one of the documented enum values, not {signal}")
        if decision and not is_placeholder(decision) and decision not in VALID_FEEDBACK_DECISIONS:
            errors.append(f"{source_name}: decision/disposition must be none/candidate/defer/deferred/already-covered, not {decision}")
        if target and not is_placeholder(target) and target not in VALID_FEEDBACK_TARGETS:
            errors.append(f"{source_name}: target must be a documented candidate target, not {target}")
        if candidate_eval_type and not is_placeholder(candidate_eval_type) and candidate_eval_type not in EVAL_CANDIDATE_TYPES and candidate_eval_type != "not-needed":
            errors.append(f"{source_name}: candidate eval type must be a documented fixture type, not {candidate_eval_type}")
        if decision not in {"", "none", "not-needed"} and is_placeholder(evidence):
            errors.append(f"{source_name}: candidate rows require source evidence")
        if decision not in {"", "none", "not-needed"}:
            if is_placeholder(attribution):
                errors.append(f"{source_name}: candidate rows require attribution_type")
            elif attribution not in VALID_ATTRIBUTION_TYPES:
                errors.append(f"{source_name}: attribution_type must be a documented enum value, not {attribution}")
            if attribution == "execution-lapse" and target in REWRITE_TARGETS:
                errors.append(f"{source_name}: execution-lapse must not target local-skill/reference/template/knowledge-promotion rewrites")
            epoch = clean_cell(row.get("task_epoch", "")).lower()
            if is_placeholder(epoch):
                errors.append(f"{source_name}: candidate rows require task_epoch to distinguish legacy/migration/current evidence")
            elif epoch not in VALID_FEEDBACK_EPOCHS:
                errors.append(f"{source_name}: task_epoch must be legacy/migration/current/not-needed")
            if epoch == "unknown":
                errors.append(f"{source_name}: unknown is only a preflight classification; do not record it as task_epoch")
            audit_lens = clean_cell(row.get("audit_lens", "")).lower()
            if not is_placeholder(audit_lens) and audit_lens not in VALID_AUDIT_LENSES:
                errors.append(f"{source_name}: audit_lens must be active/submitted/archive/not-needed")
            workflow_synced_at = clean_cell(row.get("workflow_synced_at", "")).lower()
            if workflow_synced_at in INVALID_UNKNOWN_TIMING_VALUES:
                errors.append(f"{source_name}: unknown workflow_synced_at is only a preflight classification; do not record it as a candidate row")
            for field in FEEDBACK_COHORT_FIELDS[1:]:
                if is_placeholder(row.get(field, "")):
                    errors.append(f"{source_name}: candidate rows require {field} for mechanism cohort/baseline attribution")
        if is_feedback_candidate(decision, target, candidate_eval_type) and not has_eval_guard(row_eval_guard(row)):
            errors.append(f"{source_name}: eval-candidate rows require eval guard with positive + negative fixture and failure oracle, or already-covered:<case-id>")
    return errors, checked_feedback


def validate_local_skill_rows(rows: list[dict[str, str]]) -> tuple[list[str], int]:
    errors: list[str] = []
    checked = 0
    for row in rows:
        item = clean_cell(row.get("item", ""))
        decision = clean_cell(row.get("decision", "")).lower()
        skill_type = clean_cell(row.get("type", "")).lower()
        if is_placeholder(item) and is_placeholder(decision) and is_placeholder(skill_type):
            continue
        checked += 1
        if decision and not is_placeholder(decision) and decision not in VALID_SKILL_CANDIDATE_DECISIONS:
            errors.append(f"Local Skill Candidate Log: decision must be none/candidate/update-needed/recommend-create/recommend-promote/defer, not {decision}")
        if skill_type and not is_placeholder(skill_type) and skill_type not in VALID_SKILL_CANDIDATE_TYPES:
            errors.append(f"Local Skill Candidate Log: type must be a documented skill candidate type, not {skill_type}")
        if decision in STRONG_SKILL_CANDIDATE_DECISIONS:
            required_fields = {
                "evidence": row.get("evidence", ""),
                "invocation evidence": row.get("invocation_evidence", ""),
                "silent bypass check": row.get("silent_bypass_check", "") or row.get("silent-bypass_check", ""),
                "overfit check": row.get("overfit_check", ""),
            }
            for label, value in required_fields.items():
                if is_placeholder(value):
                    errors.append(f"Local Skill Candidate Log: {decision} requires {label}")
            if not has_eval_guard(row_eval_guard(row)):
                errors.append("Local Skill Candidate Log: strong skill recommendations require trigger eval guard with positive + negative fixture and failure oracle, or already-covered:<case-id>")
    return errors, checked


def extract_named_section_value(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading)).lower()


def has_path_escape(value: str) -> bool:
    if not value or "\\" in value or value.startswith(("/", "~")):
        return True
    parts = Path(value).parts
    return any(part in {"", ".", ".."} for part in parts)


def has_symlink_component(root: Path, relative_path: str) -> bool:
    current = root.resolve()
    for part in Path(relative_path).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def safe_path_under(root: Path, relative_path: str, base_relative_path: str) -> Path | None:
    if has_path_escape(relative_path):
        return None
    root_resolved = root.resolve()
    base = (root / base_relative_path).resolve(strict=False)
    candidate = (root / relative_path).resolve(strict=False)
    try:
        if not candidate.is_relative_to(base):
            return None
    except AttributeError:
        if candidate != base and base not in candidate.parents:
            return None
    try:
        if has_symlink_component(root_resolved, relative_path):
            return None
    except OSError:
        return None
    return root / relative_path


def candidate_reference_path(root: Path, value: str) -> Path | None:
    target = clean_cell(value)
    if not target or is_placeholder(target):
        return None
    target = target.split("#", 1)[0].strip()
    target = target.strip("`")
    if target in KNOWN_REFERENCE_TARGETS:
        relative_path = KNOWN_REFERENCE_TARGETS[target]
        base_relative_path = ".agents/references" if relative_path.startswith(".agents/references/") else "."
        return safe_path_under(root, relative_path, base_relative_path)
    if target in README_TARGETS:
        return safe_path_under(root, target, str(Path(target).parent))
    for prefix in REFERENCE_PREFIXES:
        if target.startswith(prefix) and not target.endswith("/"):
            return safe_path_under(root, target, prefix.rstrip("/"))
    return None


def is_explicit_landing_marker(value: str) -> bool:
    marker = clean_cell(value).strip("`")
    if not marker or is_placeholder(marker):
        return False
    if ".." in marker or "\\" in marker or any(char.isspace() for char in marker):
        return False
    return bool(LANDING_MARKER_RE.fullmatch(marker) or RUN_EVIDENCE_MARKER_RE.match(marker))


def validate_promote_landing(root: Path, target: str, row: dict[str, str]) -> str | None:
    target_path = candidate_reference_path(root, target)
    if target_path is None:
        return f"{target}: promote target must be README.md, starter-pack/README.md, or an .agents/references/... reference target"
    if not target_path.is_file():
        return f"{target}: promote target reference does not exist; promote requires a landed reference plus landing evidence"

    landing = row_landing_evidence(row)
    landing_path = candidate_reference_path(root, landing)
    if landing_path is not None:
        if landing_path.is_file():
            return None
        return f"{target}: promote landing evidence reference does not exist"
    if is_explicit_landing_marker(landing):
        return None

    if landing and not is_placeholder(landing):
        return f"{target}: promote landing evidence must be an existing repo-local reference path or explicit evidence:<id> / marker:<id> / .agent-state/runs/<run_id>/... marker"
    return f"{target}: promote requires landing evidence pointing to the landed reference or evidence marker"


def extract_risk_tier(markdown_text: str) -> str | None:
    return wr.extract_risk_tier(markdown_text)


def has_explicit_strict_signal_section(*texts: str | None) -> bool:
    for text in texts:
        if not text:
            continue
        for heading in STRICT_SIGNAL_HEADINGS:
            if extract_section(text, heading):
                return True
    return False


def strict_trigger_required(task_plan_text: str | None, progress_text: str | None, findings_text: str) -> bool:
    tier = extract_risk_tier(task_plan_text or "")
    return (
        tier in {"high", "release"}
        or wr.has_external_system_scope(task_plan_text or "")
        or has_explicit_strict_signal_section(task_plan_text, progress_text, findings_text)
    )


def validate(
    findings_path: Path,
    task_plan_path: Path | None = None,
    progress_path: Path | None = None,
    strict_trigger: bool = False,
    check_template: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not findings_path.is_file():
        return {"status": "fail", "errors": [f"findings file not found: {findings_path}"], "warnings": []}

    if is_template_path(findings_path) and not check_template:
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "checked_rows": 0,
        }

    text = findings_path.read_text(encoding="utf-8")
    task_plan_text: str | None = None
    progress_text: str | None = None
    if task_plan_path is not None:
        if not task_plan_path.is_file():
            return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": []}
        task_plan_text = task_plan_path.read_text(encoding="utf-8")
    if progress_path is not None and progress_path.is_file():
        progress_text = progress_path.read_text(encoding="utf-8")
    root = findings_path.resolve().parent
    if task_plan_path is not None and task_plan_path.is_absolute():
        root = task_plan_path.resolve().parent

    strict_required = strict_trigger and strict_trigger_required(task_plan_text, progress_text, text)
    rows = extract_table(text, "## Knowledge Promotion")
    feedback_heading, feedback_rows = extract_first_table(text, FEEDBACK_HEADINGS)
    trace_intake_heading = ""
    trace_intake_rows: list[dict[str, str]] = []
    if progress_text:
        trace_intake_heading, trace_intake_rows = extract_first_table(progress_text, TRACE_INTAKE_HEADINGS)
    local_skill_rows = extract_table(text, "## Local Skill Candidate Log")
    checked = 0
    real_decision_rows = 0

    if strict_required and not rows:
        errors.append("strict trigger requires Knowledge Promotion rows with promote/defer/none decision")

    if strict_required:
        lower_text = "\n".join(extract_section(text, "## Knowledge Promotion")).lower()
        for term in TRACKER_TERMS:
            if term in lower_text:
                errors.append("Knowledge Promotion must not become a tracker/backlog table")
                break

    if feedback_heading:
        lower_feedback = "\n".join(extract_section(text, feedback_heading)).lower()
        for term in (*TRACKER_TERMS, *FORBIDDEN_FEEDBACK_TERMS):
            if term in lower_feedback:
                errors.append("Real Task Feedback must not become a tracker/backlog or auto-generation queue")
                break

    for row in rows:
        target = row.get("target", "<unknown target>")
        decision = clean_cell(row.get("decision", "")).lower()
        action = clean_cell(row.get("action", "")).lower()
        if is_decision_placeholder(decision):
            continue
        if decision not in VALID_DECISIONS:
            errors.append(f"{target}: decision must be promote/defer/none/not-needed/already-promoted")
            continue
        relation = clean_cell(row.get("relation", "")).lower()
        if relation and relation not in VALID_RELATIONS and not is_placeholder(relation):
            errors.append(f"{target}: relation must be new/confirms/updates/supersedes/invalidates/not-needed")
        real_decision_rows += 1
        if decision in {"none", "not-needed"}:
            reason = row_reason(row)
            if strict_required and is_placeholder(reason):
                errors.append(f"{target}: {decision} requires reason / owner under strict trigger")
            continue
        checked += 1
        for key in ("source", "trust_level", "refresh_when"):
            if is_placeholder(row.get(key, "")):
                errors.append(f"{target}: {decision} requires {key.replace('_', ' ')}")
        reason = row_reason(row)
        if decision == "defer" and is_placeholder(reason):
            errors.append(f"{target}: defer requires reason / owner")
        if decision == "already-promoted" and is_placeholder(reason):
            errors.append(f"{target}: already-promoted requires reason / owner with reference target")
        if decision == "promote" and action not in {"updated", "deferred"}:
            warnings.append(f"{target}: promote usually expects action=updated or explicit deferred reason")
        if decision == "promote":
            landing_error = validate_promote_landing(root, target, row)
            if landing_error:
                errors.append(landing_error)

    if strict_required and real_decision_rows == 0:
        errors.append("strict trigger requires at least one non-placeholder Knowledge Promotion decision row")

    feedback_errors, checked_feedback = validate_feedback_rows(
        feedback_rows,
        source_name="Real Task Feedback",
        require_signal_enum=True,
    )
    errors.extend(feedback_errors)

    trace_errors, checked_trace_intake = validate_feedback_rows(
        trace_intake_rows,
        source_name="Trace-to-Eval Intake",
        require_signal_enum=False,
    )
    errors.extend(trace_errors)

    if has_workflow_trace_intake_claim(progress_text) and checked_trace_intake == 0:
        errors.append("Workflow Trace marks trace_to_eval_intake as candidate/recorded but no structured Trace-to-Eval Intake row exists")

    skill_errors, checked_skill_candidates = validate_local_skill_rows(local_skill_rows)
    errors.extend(skill_errors)

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "checked_rows": checked,
        "checked_feedback_rows": checked_feedback,
        "checked_trace_intake_rows": checked_trace_intake,
        "checked_skill_candidate_rows": checked_skill_candidates,
        "strict_trigger_required": strict_required,
        "decision_rows": real_decision_rows,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Knowledge Promotion rows without creating a second tracker.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--findings", default="findings.md", help="Findings markdown file.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Optional task_plan.md path for --strict-trigger.")
    parser.add_argument("--progress", default="progress.md", help="Optional progress.md path for --strict-trigger.")
    parser.add_argument("--strict-trigger", action="store_true", help="Require explicit promote/defer/none decision rows for high/release or knowledge-bearing tasks.")
    parser.add_argument(
        "--check-template",
        action="store_true",
        help="Validate raw templates intentionally. By default, .agents/templates files are skipped.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    findings_path = Path(args.findings)
    if not findings_path.is_absolute():
        findings_path = root / findings_path
    task_plan_path = Path(args.task_plan)
    if not task_plan_path.is_absolute():
        task_plan_path = root / task_plan_path
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path

    payload = validate(
        findings_path,
        task_plan_path=task_plan_path if args.strict_trigger else None,
        progress_path=progress_path,
        strict_trigger=args.strict_trigger,
        check_template=args.check_template,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        for warning in payload["warnings"]:
            print(f"warning: {warning}")
        for error in payload["errors"]:
            print(f"error: {error}")
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
