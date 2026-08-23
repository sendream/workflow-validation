#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import current_task_snapshot as task_snapshot
import markdown_document as md_doc
import markdown_table as md_table
import validator_result as vr
import workflow_routing as wr


SCRIPT_DIR = Path(__file__).resolve().parent
CHILD_VALIDATOR_TIMEOUT_SECONDS = 120

# Core closeout owns identity/lifecycle, acceptance/evidence, referenced run
# manifests, and archive/handoff. Optional packages (role-review packet,
# campaign, skill curator, workflow-value) run only when the three files
# already reference them; they are not default closeout schema. Do not add
# new optional-package parsers here.

RUN_ID_PATTERNS = (
    re.compile(r"(?:Run ID|run_id)\s*[:：]\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE | re.MULTILINE),
)
RUN_ID_VALUE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
NON_RUN_REFERENCE_PREFIXES = (
    "git-commit-",
    "git-push-",
    "commit-ref-",
    "push-ref-",
)
TYPED_NON_RUN_REF_PREFIXES = (
    "commit-ref:",
    "push-ref:",
    "source-file:",
    "artifact:",
    "release-source:",
    "waiver:",
    "manual:",
)
SOURCE_ROOT_DENIED_PARTS = {
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
    "__pycache__",
}
COMMAND_EVIDENCE_SIGNAL_RE = re.compile(
    r"(\bpytest\b|\bpython3?\b|\bbash\b|\bsh\b|\bnpm\b|\bpnpm\b|\byarn\b|\bnode\b|\bgo\s+test\b|"
    r"\bmvn\b|\bgradle\b|\bcargo\b|\bgit\s+diff\b|\bpy_compile\b|run-workflow-evals|"
    r"verify-workflow-smoke|exit\s+0|terminal output|local stdout|\bstdout\b|\bstderr\b)",
    re.IGNORECASE,
)
ARTIFACT_SIGNAL_RE = re.compile(
    r"(\b(jar|container)\b"
    r"|\b(docker|container)\s+image\b"
    r"|\b(deploy|deployment|release|build)\s+(package|bundle)\b"
    r"|\.jar\b"
    r"|\b(?:dist|release|deploy|deployment|build)[\w./-]*\.(?:zip|tar\.gz)\b"
    r"|部署包|发布包|构建产物|镜像)",
    re.IGNORECASE,
)
MANIFEST_RE = re.compile(r"\.agent-state/runs/([A-Za-z0-9._-]+)/manifest\.json")
RUN_ARTIFACT_RE = re.compile(r"\.agent-state/runs/([A-Za-z0-9._-]+)(?:/|$)")
ROLE_PACKET_RE = re.compile(
    r"\.agent-state/runs/[A-Za-z0-9._-]+/"
    r"(?:role-review/[A-Za-z0-9._-]+|multi-agent-campaign/role-review/[A-Za-z0-9._-]+|isolated-review)/?"
)
CAMPAIGN_MANIFEST_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/multi-agent-campaign/campaign-manifest\.json")
EXTERNAL_BOUNDARY_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/external-content-boundary\.json")
SKILL_CURATOR_REPORT_RE = re.compile(r"\.agent-state/runs/[A-Za-z0-9._-]+/skill-evolution/curator-report\.json")
WORKFLOW_VALUE_REPORT_RE = re.compile(
    r"\.agent-state/runs/[A-Za-z0-9._-]+/(?:harness-evolution/)?workflow-value-report\.json"
)
UI_BROWSER_SIGNAL_RE = re.compile(
    r"\b(ui|browser|frontend|visual|screenshot|playwright|cypress)\b|界面|页面|浏览器|截图|视觉",
    re.IGNORECASE,
)
UI_RESULT_PASS = {"pass", "passed", "manual", "done", "ok"}
WAIVER_SHIP_ACCEPTED = {"yes", "conditional"}
LOCAL_UI_ARTIFACT_RE = re.compile(
    r"(?P<path>(?:\.agent-state/|\.agents/runs/|\.agents/|\./|\.\./)[^\s|]+"
    r"|[A-Za-z0-9_.-]+/[^\s|]+\.(?:txt|log|json|html|md|png|jpg|jpeg|webp|har|trace|zip))",
    re.IGNORECASE,
)
CLOSEOUT_ALLOWED_FINAL_STATUSES = wr.CLOSEOUT_ALLOWED_FINAL_STATUSES
ACTIVE_LIFECYCLE_STATES = {"planned", "in_progress", "active", "implementing"}
PRE_SUBMIT_LIFECYCLE_STATES = {"planned", "in_progress", "active", "implementing", "verifying", "ready_to_submit"}
SUBMITTED_LIFECYCLE_STATES = {"submitted", "archived"}
VALID_LIFECYCLE_STATES = PRE_SUBMIT_LIFECYCLE_STATES | SUBMITTED_LIFECYCLE_STATES | {"blocked", "deferred", "cancelled"}
VAGUE_NEXT_ACTION_PATTERNS = (
    r"^\s*(?:continue|continue work|follow up|fix later|todo|tbd|next|next step|next action)\s*$",
    r"^\s*(?:继续|继续推进|继续优化|下一步|后续处理|待处理|待办|稍后修复)\s*$",
    r"^\s*(?:继续|后续|下一步).{0,12}$",
)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def is_not_needed_like(value: str) -> bool:
    return clean(value).lower() in {"not-needed", "not needed", "none", "n/a", "na"}


def is_placeholder(value: str) -> bool:
    normalized = clean(value).lower()
    if not normalized:
        return True
    if "待填写" in normalized:
        return True
    return normalized in {
        "pending",
        "missing",
        "required",
        "optional",
        "unknown",
        "not-created",
        "not created",
        "not-needed",
        "not needed",
        "none",
        "n/a",
        "na",
    }


def validate_next_action_quality(progress_text: str) -> list[str]:
    match = re.search(r"(?im)^\s*-\s*Next Action\s*[:：]\s*(.+?)\s*$", progress_text)
    if not match:
        return []
    raw = clean(match.group(1))
    normalized = raw.lower()
    if not raw or "待填写" in normalized or normalized in {"missing", "pending", "required"}:
        return ["Next Action must be concrete or explicitly not-needed before strict closeout"]
    if normalized in {"not-needed", "not needed", "none", "completed", "done", "已完成"}:
        return []
    for pattern in VAGUE_NEXT_ACTION_PATTERNS:
        if re.search(pattern, raw, re.IGNORECASE):
            return ["Next Action is too vague for strict closeout; write one executable next step, verification, or stop condition"]
    return []


def valid_run_id(value: str) -> bool:
    value = clean(value)
    lowered = value.lower()
    if not value:
        return False
    if "待填写" in lowered:
        return False
    if lowered in {
        "run_id",
        "trace_id",
        "trace id",
        "optional",
        "none",
        "not-needed",
        "not needed",
        "not-created",
        "not created",
        "n/a",
        "na",
        "pending",
        "missing",
        "required",
        "optional / 待填写",
    }:
        return False
    if any(part in value for part in ("/", "\\", "..", " ")):
        return False
    return bool(RUN_ID_VALUE_RE.fullmatch(value))


def is_non_run_reference_id(value: str) -> bool:
    normalized = clean(value).lower()
    return normalized.startswith(NON_RUN_REFERENCE_PREFIXES)


def has_typed_non_run_reference(value: str) -> bool:
    normalized = clean(value).lower()
    return any(prefix in normalized for prefix in TYPED_NON_RUN_REF_PREFIXES) or any(
        prefix in normalized for prefix in NON_RUN_REFERENCE_PREFIXES
    )


def has_run_manifest_reference(value: str) -> bool:
    cleaned = clean(value)
    if "manifest:" in cleaned.lower():
        ref = wr.parse_evidence_ref(cleaned)
        if ref and ref.ref_type == "manifest" and MANIFEST_RE.search(ref.target):
            return True
    return bool(MANIFEST_RE.search(cleaned))


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def extract_section(markdown_text: str, heading: str) -> list[str]:
    return md_doc.section_lines(markdown_text, heading)


def section_text(markdown_text: str, heading: str) -> str:
    return md_doc.section_text(markdown_text, heading)


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("/", "_")


def split_markdown_row(line: str) -> list[str]:
    return md_table.split_markdown_table_row(line)


def is_separator_row(cells: list[str]) -> bool:
    return md_table.is_separator_row(cells)


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=False,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def section_contains_table(section: list[str]) -> bool:
    return any(line.strip().startswith("|") for line in section)


def risk_tier(task_plan_text: str) -> str:
    return wr.risk_tier_or_unknown(task_plan_text)


def has_external_scope(task_plan_text: str) -> bool:
    return wr.has_external_system_scope(task_plan_text)


def has_release_artifact_signal(task_plan_text: str, progress_text: str) -> bool:
    release_gate_removed = re.sub(
        r"(?ms)^## Release Artifact Source Gate\n.*?(?=^## |\Z)",
        "",
        progress_text,
    )
    return bool(ARTIFACT_SIGNAL_RE.search(task_plan_text) or ARTIFACT_SIGNAL_RE.search(release_gate_removed))


def extract_active_task_id(markdown_text: str, source_name: str) -> str | None:
    return task_snapshot.extract_active_task_id(markdown_text, source_name)


def validate_active_ids(
    task_plan_text: str,
    progress_text: str,
    findings_text: str | None,
    strict: bool,
    snapshot: task_snapshot.CurrentTaskSnapshot | None = None,
) -> dict[str, Any]:
    """Validate active-task identity from the shared snapshot when available.

    Custom paths retain the compatibility fallback below. Standard root state
    must not be parsed a second time here: a partial or conflicting shared
    snapshot is the authoritative fact-domain failure and carries bounded
    source digests for diagnosis.
    """

    if snapshot is not None:
        errors: list[str] = []
        if strict and snapshot.source_status != "complete":
            errors.append(
                "active task id mismatch or incomplete across task_plan/progress/findings "
                f"(shared current task snapshot: {snapshot.source_status})"
            )
        if strict and snapshot.task_id is None and not errors:
            errors.append("active task id is missing from shared current task snapshot")
        return {
            "status": "pass" if not errors else "fail",
            "task_id": snapshot.task_id,
            "source_status": snapshot.source_status,
            "source_digests": snapshot.source_digests,
            "source": "current_task_snapshot",
            "errors": errors,
        }

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
    if strict and missing:
        errors.append("active task id is missing from: " + ", ".join(missing))
    if len(unique) > 1:
        errors.append("active task id mismatch across task_plan/progress/findings: " + ", ".join(f"{name}={value}" for name, value in present.items()))
    return {"status": "pass" if not errors else "fail", "ids": ids, "errors": errors}


def scripts_dir(root: Path) -> Path:
    candidate = root / ".agents" / "scripts"
    if (candidate / "validate-evidence-waivers.py").is_file():
        return candidate
    return SCRIPT_DIR


def run_validator(name: str, command: list[str], cwd: Path) -> dict[str, Any]:
    return vr.run_json_validator(name, command, cwd, timeout=CHILD_VALIDATOR_TIMEOUT_SECONDS).as_dict()


def run_fact_domain_validators_once(
    validators: list[tuple[str, list[str]]],
    cwd: Path,
    checks: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    """Execute each declared fact-domain command once and retain its ownership trace."""

    seen_names: set[str] = set()
    seen_commands: set[tuple[str, ...]] = set()
    executed: list[str] = []
    skipped_duplicates: list[str] = []
    for name, command in validators:
        command_key = tuple(command)
        if name in seen_names or command_key in seen_commands:
            skipped_duplicates.append(name)
            errors.append(f"duplicate fact-domain validator declaration: {name}")
            continue
        seen_names.add(name)
        seen_commands.add(command_key)
        executed.append(name)
        if len(command) < 2 or not Path(command[1]).is_file():
            errors.append(f"{name} validator is missing: {command[1] if len(command) > 1 else '<missing>'}")
            continue
        result = run_validator(name, command, cwd)
        checks[name] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            errors.append(f"{name} validator failed")
    return {
        "status": "pass" if not skipped_duplicates else "fail",
        "executed": executed,
        "unique_command_count": len(seen_commands),
        "duplicate_declarations": skipped_duplicates,
    }


def run_ids_from_text(value: str) -> set[str]:
    run_ids: set[str] = set()
    run_ids.update(MANIFEST_RE.findall(value))
    run_ids.update(RUN_ARTIFACT_RE.findall(value))
    return {run_id for run_id in run_ids if valid_run_id(run_id) and not is_non_run_reference_id(run_id)}


def structured_run_ids(markdown_text: str) -> list[str]:
    run_ids: set[str] = set()
    for heading in (
        "## Active Task Snapshot",
        "## Traceability",
        "## Current Status",
        "## Delivery Metadata",
        "## Session Reviewer Authorization",
        "## Reviewer Start Authority",
    ):
        section_lines = extract_section(markdown_text, heading)
        section = "\n".join(section_lines)
        if not section:
            continue

        for pattern in RUN_ID_PATTERNS:
            for match in pattern.findall(section):
                value = clean(match)
                if valid_run_id(value):
                    run_ids.add(value)

        if section_contains_table(section_lines):
            header: list[str] | None = None
            for line in section_lines:
                if not line.strip().startswith("|"):
                    continue
                cells = split_markdown_row(line)
                if header is None:
                    header = [normalize_key(cell) for cell in cells]
                    continue
                if is_separator_row(cells):
                    continue
                if len(cells) != len(header):
                    continue
                row = dict(zip(header, cells))
                for key, value in row.items():
                    if key in {"run_id", "run"} and valid_run_id(value) and not is_non_run_reference_id(value):
                        run_ids.add(value)
                if (
                    "item" in row
                    and normalize_key(row["item"]) in {"run_id", "run"}
                    and valid_run_id(row.get("value", ""))
                    and not is_non_run_reference_id(row.get("value", ""))
                ):
                    run_ids.add(row["value"])
    return sorted(run_ids)


def evidence_referenced_run_ids(task_plan_text: str, progress_text: str, findings_text: str | None) -> list[str]:
    run_ids: set[str] = set()

    evidence_tables = (
        (task_plan_text, "## Verification Matrix", ("evidence",)),
        (task_plan_text, "## Evidence Required Before Done", ("evidence", "artifact")),
        (progress_text, "## Workflow Trace", ("evidence",)),
        (progress_text, "## Run Evidence", ("run_id", "manifest___artifact", "manifest_artifact", "artifact", "notes")),
        (progress_text, "## Validation", ("artifact", "evidence")),
        (progress_text, "## Acceptance Evidence", ("evidence", "evidence_location", "notes", "artifact")),
        (progress_text, "## Final Evidence Ledger", ("supplemental_evidence", "artifact")),
        (progress_text, "## Role Review Summary", ("packet",)),
    )
    for text, heading, keys in evidence_tables:
        for row in extract_table(text, heading):
            for key in keys:
                value = clean(row.get(key, ""))
                if key == "run_id" and valid_run_id(value) and not is_non_run_reference_id(value):
                    run_ids.add(value)
                run_ids.update(run_ids_from_text(value))

    if findings_text:
        for row in extract_table(findings_text, "## Real Task Feedback Loop"):
            for key in ("source_evidence", "candidate_artifact"):
                run_ids.update(run_ids_from_text(clean(row.get(key, ""))))
    return sorted(run_ids)


def referenced_run_evidence_ids(progress_text: str) -> list[str]:
    run_ids: set[str] = set()
    for row in extract_table(progress_text, "## Run Evidence"):
        value = clean(row.get("run_id", ""))
        if valid_run_id(value) and not is_non_run_reference_id(value):
            run_ids.add(value)
    return sorted(run_ids)


def contract_row_is_used(row: dict[str, str]) -> bool:
    status = clean(row.get("result", "") or row.get("status", "")).lower()
    return status == "used"


def row_artifact_evidence(row: dict[str, str]) -> str:
    return clean(
        row.get("artifact___evidence", "")
        or row.get("artifact_evidence", "")
        or row.get("artifact", "")
        or row.get("evidence", "")
    )


def external_content_boundary_artifacts(task_plan_text: str, progress_text: str) -> tuple[list[str], list[str]]:
    artifacts: set[str] = set()
    errors: list[str] = []
    contract_rows: list[tuple[str, dict[str, str]]] = [
        ("progress", row) for row in extract_table(progress_text, "## Tool / Prompt / Command Contract Evidence")
    ]
    contract_rows.extend(
        ("task_plan", row) for row in extract_table(task_plan_text, "## Tool / Prompt / Command Contracts")
    )
    for source, row in contract_rows:
        contract_id = clean(row.get("contract_id", ""))
        trigger = clean(row.get("trigger", "")).lower()
        if is_placeholder(contract_id) or "external-content-derived-command" not in trigger or not contract_row_is_used(row):
            continue
        evidence = row_artifact_evidence(row)
        matches = EXTERNAL_BOUNDARY_RE.findall(evidence)
        if not matches:
            errors.append(
                f"external-content-derived-command {contract_id} in {source}: strict closeout requires .agent-state/runs/<run_id>/external-content-boundary.json artifact"
            )
        artifacts.update(matches)
    return sorted(artifacts), errors


def release_ui_browser_signal(task_plan_text: str, progress_text: str) -> bool:
    selected = "\n".join(
        [
            section_text(task_plan_text, "## Risk Tier"),
            section_text(task_plan_text, "## Requirement Contract"),
            section_text(task_plan_text, "## Scope"),
            section_text(task_plan_text, "## Behavior Scenarios"),
            section_text(task_plan_text, "## Example Table"),
            section_text(task_plan_text, "## Verification Matrix"),
            section_text(task_plan_text, "## Acceptance Evidence Map"),
            section_text(task_plan_text, "## Test Strategy"),
            section_text(task_plan_text, "## Test Evidence Gate"),
            section_text(progress_text, "## Changed Files Manifest"),
            section_text(progress_text, "## Final Evidence Ledger"),
            section_text(progress_text, "## Browser / UI Evidence"),
            section_text(progress_text, "## Test Evidence Gate"),
        ]
    )
    return bool(UI_BROWSER_SIGNAL_RE.search(selected))


def local_ui_artifact_paths(value: str) -> list[str]:
    return [match.group("path").rstrip(".,;)\"'") for match in LOCAL_UI_ARTIFACT_RE.finditer(clean(value))]


def valid_ui_artifact(root: Path, value: str, require_existing_artifacts: bool) -> tuple[bool, list[str]]:
    errors: list[str] = []
    paths = local_ui_artifact_paths(value)
    if not paths:
        return False, errors
    valid = False
    for path_value in paths:
        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError:
            errors.append(f"Browser / UI Evidence local artifact must stay under project root: {path_value}")
            continue
        if require_existing_artifacts and not candidate.exists():
            errors.append(f"Browser / UI Evidence local artifact does not exist: {path_value}")
            continue
        valid = True
    return valid, errors


def browser_ui_evidence_present(root: Path, progress_text: str, require_existing_artifacts: bool) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for row in extract_table(progress_text, "## Browser / UI Evidence"):
        evidence = clean(row.get("evidence", ""))
        result = clean(row.get("result", "")).lower()
        notes = clean(row.get("notes", ""))
        path_or_command = clean(row.get("path___command", "") or row.get("path_command", ""))
        if is_placeholder(evidence) or is_not_needed_like(evidence):
            continue
        if result not in UI_RESULT_PASS:
            continue
        valid_artifact, artifact_errors = valid_ui_artifact(root, path_or_command, require_existing_artifacts)
        errors.extend(artifact_errors)
        if valid_artifact:
            return True, errors
    for row in extract_table(progress_text, "## Verification Waivers"):
        combined = " ".join(row.values()).lower()
        allowed = clean(row.get("allowed_to_ship", "")).lower()
        substitute = clean(row.get("substitute_evidence", ""))
        if (
            UI_BROWSER_SIGNAL_RE.search(combined)
            and not is_placeholder(row.get("reason", ""))
            and allowed in WAIVER_SHIP_ACCEPTED
            and not is_placeholder(substitute)
        ):
            return True, errors
    return False, errors


def workflow_trace_step_status(progress_text: str, step_name: str) -> str:
    wanted = normalize_key(step_name)
    for row in extract_table(progress_text, "## Workflow Trace"):
        step = normalize_key(row.get("step", ""))
        if step == wanted:
            return clean(row.get("status", "")).lower().replace(" ", "_").replace("-", "_")
    return ""


def current_status_values(progress_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in extract_section(progress_text, "## Current Status"):
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith(">"):
            continue
        stripped = stripped.lstrip("-* ").strip()
        if ":" in stripped:
            key, value = stripped.split(":", 1)
        elif "：" in stripped:
            key, value = stripped.split("：", 1)
        else:
            continue
        values[normalize_key(key)] = clean(value)
    for row in extract_table(progress_text, "## Current Status"):
        key = normalize_key(row.get("item", "") or row.get("field", "") or row.get("key", ""))
        value = clean(row.get("value", ""))
        if key and value:
            values[key] = value
    return values


def lifecycle_state_from_progress(progress_text: str) -> str:
    values = current_status_values(progress_text)
    for key in ("lifecycle_state", "task_lifecycle", "task_state", "phase", "current_phase", "status", "三文件状态"):
        value = clean(values.get(key, "")).lower().replace("-", "_").replace(" ", "_")
        if value in VALID_LIFECYCLE_STATES:
            return value
    return ""


def archived_or_cleared_from_progress(progress_text: str) -> bool:
    values = current_status_values(progress_text)
    combined = "\n".join(extract_section(progress_text, "## Current Status") + extract_section(progress_text, "## Handoff")).lower()
    archive_status = clean(values.get("归档状态", "") or values.get("archive_status", "")).lower()
    three_file_status = clean(values.get("三文件状态", "")).lower()
    return (
        archive_status.startswith("archived-at")
        or "archived-at `.agents/tasks/" in combined
        or "archived at `.agents/tasks/" in combined
        or three_file_status in {"archived", "reset", "cleared", "no-active-task", "no active task"}
    )


def archive_status_from_progress(progress_text: str) -> str:
    values = current_status_values(progress_text)
    return clean(values.get("归档状态", "") or values.get("archive_status", "")).lower()


def active_lifecycle_closeout_check(
    progress_text: str,
    require_closeout_state: bool = False,
    snapshot_lifecycle_state: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    lifecycle = snapshot_lifecycle_state or lifecycle_state_from_progress(progress_text)
    lifecycle = lifecycle.lower().replace("-", "_").replace(" ", "_")
    task_closeout_status = workflow_trace_step_status(progress_text, "task_closeout")
    archived_or_cleared = archived_or_cleared_from_progress(progress_text)
    archive_status = archive_status_from_progress(progress_text)

    closeout_complete = task_closeout_status in {"strict_pass", "focused", "checked", "done", "completed", "pass", "passed"}

    if require_closeout_state:
        if not lifecycle:
            errors.append("strict closeout requires Current Status Lifecycle state to be planned/in_progress/verifying/ready_to_submit/submitted/archived/blocked/deferred/cancelled")
        if re.search(r"(?im)^## +Workflow Trace\s*$", progress_text):
            if not task_closeout_status:
                errors.append("strict closeout requires Workflow Trace task_closeout focused/strict-pass/strict-fail/not-needed with evidence")
            elif task_closeout_status in {"not_needed", "not-needed"}:
                errors.append("strict closeout requires task_closeout focused/strict-pass/strict-fail/blocked; not-needed is only for fast path or omitted closeout")
            elif task_closeout_status in {"strict_fail", "strict-fail", "blocked", "fail", "failed", "missing"}:
                errors.append(f"task_closeout is {task_closeout_status}; resolve closeout blockers before final handoff")
        if not archive_status:
            errors.append("strict closeout requires Current Status Archive status: archived-at / archive-ready / archive-deferred")
        elif archive_status.startswith("not-needed"):
            errors.append("strict closeout requires archive-ready, archive-deferred, or archived-at; not-needed is only for fast path or omitted closeout")
        elif not (
            archive_status.startswith("archived-at")
            or archive_status.startswith("archive-ready")
            or archive_status.startswith("archive-deferred")
        ):
            errors.append(f"strict closeout Archive status is not recognized: {archive_status}")

    if closeout_complete and lifecycle in ACTIVE_LIFECYCLE_STATES:
        errors.append(
            f"task_closeout is {task_closeout_status}, but Current Status lifecycle remains {lifecycle}; move to ready_to_submit/submitted/archived or record a blocker"
        )
    return {
        "status": "pass" if not errors else "fail",
        "lifecycle_state": lifecycle or "<missing>",
        "task_closeout_status": task_closeout_status or "<missing>",
        "archive_status": archive_status or "<missing>",
        "archived_or_cleared": archived_or_cleared,
        "errors": errors,
    }


def referenced_role_review_packets(progress_text: str) -> list[str]:
    paths: set[str] = set()
    for match in ROLE_PACKET_RE.findall(progress_text):
        candidate = clean(match).rstrip("/")
        if candidate and "<" not in candidate and ">" not in candidate:
            paths.add(candidate)

    for row in extract_table(progress_text, "## Isolated Reviewer"):
        value = clean(row.get("value", ""))
        if ROLE_PACKET_RE.fullmatch(value.rstrip("/") + "/"):
            paths.add(value.rstrip("/"))

    for row in extract_table(progress_text, "## Role Review Summary"):
        packet = clean(row.get("packet", "")).rstrip("/")
        if ROLE_PACKET_RE.fullmatch(packet + "/"):
            paths.add(packet)

    return sorted(paths)


def referenced_dynamic_agent_campaigns(progress_text: str) -> list[str]:
    campaigns: set[str] = set()
    for match in CAMPAIGN_MANIFEST_RE.findall(progress_text):
        campaigns.add(match.removesuffix("/campaign-manifest.json"))
    return sorted(campaigns)


def referenced_skill_curator_reports(task_plan_text: str, progress_text: str, findings_text: str | None) -> list[str]:
    paths: set[str] = set()
    for text in (task_plan_text, progress_text, findings_text or ""):
        for match in SKILL_CURATOR_REPORT_RE.findall(text):
            paths.add(clean(match))
    return sorted(paths)


def referenced_workflow_value_reports(task_plan_text: str, progress_text: str, findings_text: str | None) -> list[str]:
    paths: set[str] = set()
    for text in (task_plan_text, progress_text, findings_text or ""):
        for match in WORKFLOW_VALUE_REPORT_RE.findall(text):
            paths.add(clean(match))
    return sorted(paths)


def human_needed_items(payload: dict[str, Any]) -> list[str]:
    rows = payload.get("human_needed", [])
    if not isinstance(rows, list):
        return []
    result: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = clean(str(row.get("item", "")))
        if item:
            result.append(item)
    return result


def skill_curator_closeout_surface(progress_text: str, report_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    items = human_needed_items(payload)
    if not items:
        return {"status": "pass", "human_needed_items": [], "errors": []}

    rows = extract_table(progress_text, "## Skill Curator Closeout")
    errors: list[str] = []
    if not rows:
        return {
            "status": "fail",
            "human_needed_items": items,
            "errors": ["skill curator human-needed items require progress.md#Skill Curator Closeout"],
        }

    values: dict[str, str] = {}
    for row in rows:
        key = normalize_key(row.get("item", "") or row.get("field", "") or row.get("key", ""))
        value = clean(row.get("value", ""))
        if key:
            values[key] = value

    section = section_text(progress_text, "## Skill Curator Closeout")
    surfaced = clean(values.get("human-needed_surfaced", values.get("human_needed_surfaced", ""))).lower()
    report_value = clean(values.get("curator_report", values.get("report", "")))
    disposition = clean(
        values.get(
            "question___disposition",
            values.get("question_disposition", values.get("disposition", values.get("next_action", ""))),
        )
    )
    if report_path not in section and report_path not in report_value:
        errors.append(f"Skill Curator Closeout must cite referenced curator report: {report_path}")
    if surfaced not in {"yes", "asked-user", "recorded", "deferred", "rejected", "user-approved", "record-only"}:
        errors.append("Skill Curator Closeout must set Human-needed surfaced=yes/asked-user/recorded/deferred/rejected/user-approved")
    if not disposition or is_placeholder(disposition) or is_not_needed_like(disposition):
        errors.append("Skill Curator Closeout needs a bounded question or disposition for human-needed items")
    if not any(token in disposition.lower() for token in ("ask", "user", "record", "reject", "defer", "approved", "question", "人工", "用户", "记录", "拒绝", "延期")):
        errors.append("Skill Curator Closeout disposition must show ask-user, record-only, reject, defer, or approved-scope")
    for item in items:
        if item not in section:
            errors.append(f"Skill Curator Closeout must mention human-needed item: {item}")
    return {"status": "pass" if not errors else "fail", "human_needed_items": items, "errors": errors}


def validate_referenced_skill_curator_reports(
    root: Path,
    scripts: Path,
    task_plan_text: str,
    progress_text: str,
    findings_text: str | None,
    require_existing_artifacts: bool,
) -> tuple[dict[str, Any], list[str]]:
    report_paths = referenced_skill_curator_reports(task_plan_text, progress_text, findings_text)
    check: dict[str, Any] = {"paths": report_paths, "status": "pass", "reports": {}}
    errors: list[str] = []
    for report_path in report_paths:
        report_file = root / report_path
        try:
            resolved_report = report_file.resolve(strict=False)
            resolved_report.relative_to(root.resolve())
        except ValueError:
            check["status"] = "fail"
            errors.append(f"referenced skill curator report escapes project root: {report_path}")
            continue
        if report_file.is_symlink():
            check["status"] = "fail"
            errors.append(f"referenced skill curator report must not be a symlink: {report_path}")
            continue
        if require_existing_artifacts and not report_file.is_file():
            check["status"] = "fail"
            errors.append(f"referenced skill curator report is missing: {report_path}")
            continue
        if not report_file.is_file():
            check["status"] = "fail"
            errors.append(f"referenced skill curator report is missing: {report_path}")
            continue
        command = [
            sys.executable,
            str(scripts / "validate-skill-curator-report.py"),
            "--root",
            str(root),
            "--report",
            report_path,
            "--format",
            "json",
        ]
        result = run_validator(f"skill_curator_report:{report_path}", command, root)
        report_check: dict[str, Any] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            check["status"] = "fail"
            errors.append(f"skill curator report validator failed: {report_path}")
        else:
            try:
                payload = json.loads(report_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, dict):
                surface = skill_curator_closeout_surface(progress_text, report_path, payload)
                report_check["human_needed_surface"] = surface
                if surface["status"] != "pass":
                    check["status"] = "fail"
                    errors.extend(surface["errors"])
        check["reports"][report_path] = report_check
    return check, errors


WORKFLOW_VALUE_HUMAN_DECISION_LEVELS = {
    "surface-required": 1,
    "answer-required": 2,
    "risk-acceptance-required": 3,
}


def workflow_value_human_decisions(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = payload.get("human_decisions", [])
    if not isinstance(rows, list):
        return (
            [{"decision_id": "workflow-value-report", "decision_level": "surface-required"}]
            if payload.get("human_decision_required") is True
            else []
        )
    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = clean(str(row.get("decision_level", ""))).lower()
        decision_id = clean(str(row.get("decision_id", "")))
        if level in WORKFLOW_VALUE_HUMAN_DECISION_LEVELS and decision_id:
            result.append({"decision_id": decision_id, "decision_level": level})
    if payload.get("human_decision_required") is True and not result:
        result.append({"decision_id": "workflow-value-report", "decision_level": "surface-required"})
    return result


def workflow_value_human_decision_items(payload: dict[str, Any]) -> list[str]:
    return [item["decision_id"] for item in workflow_value_human_decisions(payload)]


def workflow_value_report_boundary_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("type") != "workflow-value-report":
        errors.append("workflow value report must set type=workflow-value-report")
    if payload.get("report_only") is not True:
        errors.append("workflow value report must be report_only=true")
    status = clean(str(payload.get("status", ""))).lower()
    if status in {"error", "fail", "failed"}:
        errors.append("workflow value report must not be referenced with error/fail status")
    if payload.get("errors"):
        errors.append("workflow value report must not contain errors when referenced for closeout")
    if "human_decision_required" in payload and not isinstance(payload.get("human_decision_required"), bool):
        errors.append("workflow value report human_decision_required must be boolean")
    if "human_decisions" in payload and not isinstance(payload.get("human_decisions"), list):
        errors.append("workflow value report human_decisions must be a list")
    for field in (
        "default_gate",
        "runner",
        "live_llm",
        "state_source",
        "writes_default",
        "business_files_scanned",
        "raw_logs_scanned",
    ):
        if payload.get(field) is not False:
            errors.append(f"workflow value report must set {field}=false")
    return errors


def workflow_value_human_decision_surface(progress_text: str, report_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    decisions = workflow_value_human_decisions(payload)
    items = [item["decision_id"] for item in decisions]
    if not items:
        return {"status": "pass", "human_decision_items": [], "errors": []}

    rows = extract_table(progress_text, "## Human Decision Surface")
    errors: list[str] = []
    if not rows:
        return {
            "status": "fail",
            "human_decision_items": items,
            "errors": ["workflow value human decisions require progress.md#Human Decision Surface"],
        }

    section = section_text(progress_text, "## Human Decision Surface")
    if report_path not in section:
        errors.append(f"Human Decision Surface must cite referenced workflow value report: {report_path}")

    rows_by_id = {
        clean(row.get("decision_id", "")): row
        for row in rows
        if clean(row.get("decision_id", ""))
    }
    allowed_surfaced = {"yes", "asked-user", "recorded", "deferred", "rejected", "user-approved"}
    for decision in decisions:
        item = decision["decision_id"]
        required_level = decision["decision_level"]
        row = rows_by_id.get(item)
        if row is None:
            errors.append(f"Human Decision Surface must mention workflow value decision: {item}")
            continue
        source = clean(row.get("source", "")).lower()
        level = clean(row.get("level", "")).lower()
        surfaced = clean(row.get("surfaced", "")).lower()
        default = clean(row.get("default_recommendation", ""))
        options = clean(row.get("options", ""))
        disposition = clean(row.get("disposition", ""))
        scope = clean(row.get("authorization_scope", ""))
        evidence = clean(row.get("evidence", ""))
        if source != "workflow-value-report":
            errors.append(f"Human Decision Surface {item}: source must be workflow-value-report")
        if level not in WORKFLOW_VALUE_HUMAN_DECISION_LEVELS:
            errors.append(f"Human Decision Surface {item}: level must be surface-required/answer-required/risk-acceptance-required")
        elif WORKFLOW_VALUE_HUMAN_DECISION_LEVELS[level] < WORKFLOW_VALUE_HUMAN_DECISION_LEVELS[required_level]:
            errors.append(f"Human Decision Surface {item}: level must not downgrade report decision level {required_level}")
        if report_path not in evidence:
            errors.append(f"Human Decision Surface {item}: evidence must cite referenced workflow value report")
        if surfaced not in allowed_surfaced:
            errors.append(f"Human Decision Surface {item}: surfaced must show yes/asked-user/recorded/deferred/rejected/user-approved")
        if is_placeholder(default) or is_not_needed_like(default):
            errors.append(f"Human Decision Surface {item}: default recommendation is required")
        if is_placeholder(options) or is_not_needed_like(options):
            errors.append(f"Human Decision Surface {item}: bounded options are required")
        if not disposition or is_placeholder(disposition) or is_not_needed_like(disposition):
            errors.append(f"Human Decision Surface {item}: disposition is required")
        lowered_disposition = disposition.lower()
        if "record-only" in lowered_disposition:
            errors.append(f"Human Decision Surface {item}: surface-required decision cannot be record-only")
        if "user-approved" in lowered_disposition and (is_placeholder(scope) or is_not_needed_like(scope)):
            errors.append(f"Human Decision Surface {item}: user-approved disposition requires authorization scope")
        if "record-only" in lowered_disposition and "user-approved" in lowered_disposition:
            errors.append(f"Human Decision Surface {item}: record-only cannot also be user-approved")
    return {"status": "pass" if not errors else "fail", "human_decision_items": items, "errors": errors}


def validate_referenced_workflow_value_reports(
    root: Path,
    task_plan_text: str,
    progress_text: str,
    findings_text: str | None,
) -> tuple[dict[str, Any], list[str]]:
    report_paths = referenced_workflow_value_reports(task_plan_text, progress_text, findings_text)
    check: dict[str, Any] = {"paths": report_paths, "status": "pass", "reports": {}}
    errors: list[str] = []
    for report_path in report_paths:
        report_file = root / report_path
        try:
            resolved_report = report_file.resolve(strict=False)
            resolved_report.relative_to(root.resolve())
        except ValueError:
            check["status"] = "fail"
            errors.append(f"referenced workflow value report escapes project root: {report_path}")
            continue
        if report_file.is_symlink():
            check["status"] = "fail"
            errors.append(f"referenced workflow value report must not be a symlink: {report_path}")
            continue
        if not report_file.is_file():
            check["status"] = "fail"
            errors.append(f"referenced workflow value report is missing: {report_path}")
            continue
        try:
            payload = json.loads(report_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            check["status"] = "fail"
            errors.append(f"referenced workflow value report is invalid json: {report_path}")
            continue
        if not isinstance(payload, dict):
            check["status"] = "fail"
            errors.append(f"referenced workflow value report must be a JSON object: {report_path}")
            continue
        boundary_errors = workflow_value_report_boundary_errors(payload)
        surface = workflow_value_human_decision_surface(progress_text, report_path, payload)
        report_check = {
            "status": "pass" if not boundary_errors and surface["status"] == "pass" else "fail",
            "boundary_errors": boundary_errors,
            "human_decision_surface": surface,
        }
        if report_check["status"] != "pass":
            check["status"] = "fail"
            errors.extend(boundary_errors)
            errors.extend(surface["errors"])
        check["reports"][report_path] = report_check
    return check, errors


def packets_requiring_role_review_result(progress_text: str, packet_paths: list[str]) -> set[str]:
    required: set[str] = set()
    started = started_role_reviewer(progress_text)
    if not started:
        return required

    non_started_verdicts = {
        "",
        "not-needed",
        "not-created",
        "packet-invalid",
        "brief-invalid",
        "validator-failed",
        "tool-unavailable",
        "runtime-policy-blocked",
        "explicit-delegation-required",
        "review-incomplete",
        "reviewer-timeout",
        "budget-exceeded",
        "explicit-denied",
        "not-authorized",
    }

    for row in extract_table(progress_text, "## Isolated Reviewer"):
        item = normalize_key(row.get("item", "") or row.get("field", ""))
        value = clean(row.get("value", "")).rstrip("/")
        if item == "input_package" and ROLE_PACKET_RE.fullmatch(value + "/"):
            required.add(value)

    for row in extract_table(progress_text, "## Role Review Summary"):
        packet = clean(row.get("packet", "")).rstrip("/")
        verdict = clean(row.get("verdict", "")).lower()
        if packet and ROLE_PACKET_RE.fullmatch(packet + "/") and verdict not in non_started_verdicts:
            required.add(packet)

    if not required:
        required.update(packet_paths)
    return required


def started_role_reviewer(progress_text: str) -> bool:
    for row in extract_table(progress_text, "## Isolated Reviewer"):
        item = normalize_key(row.get("item", "") or row.get("field", ""))
        if item == "start_result":
            value = clean(row.get("value", "")).lower()
            if value in wr.REVIEWER_STARTED_RESULTS:
                return True
    for row in extract_table(progress_text, "## Workflow Trace"):
        step = normalize_key(row.get("step", ""))
        status = clean(row.get("status", "")).lower()
        if step == "isolated_reviewer" and status in wr.REVIEWER_STARTED_RESULTS:
            return True
    return False


def final_ledger_status_check(progress_text: str) -> dict[str, Any]:
    errors: list[str] = []
    rows = extract_table(progress_text, "## Final Evidence Ledger")
    real_rows = [
        row
        for row in rows
        if clean(row.get("acceptance_id", "")).lower() not in {"", "not-needed", "待填写"}
    ]
    for row in real_rows:
        acceptance_id = clean(row.get("acceptance_id", "<unknown>"))
        final_status = clean(row.get("final_status", "")).upper()
        if final_status not in CLOSEOUT_ALLOWED_FINAL_STATUSES:
            errors.append(
                f"ledger {acceptance_id}: closeout requires final status PASS/MANUAL/WAIVED/NOT_APPLICABLE, not {final_status or '<empty>'}"
            )
    return {"status": "pass" if not errors else "fail", "checked_rows": len(real_rows), "errors": errors}


def typed_reference_evidence_check(progress_text: str) -> dict[str, Any]:
    errors: list[str] = []
    checked_rows = 0
    for row in extract_table(progress_text, "## Run Evidence"):
        run_id = clean(row.get("run_id", ""))
        status = clean(row.get("status", "")).lower()
        combined = " ".join(clean(value) for value in row.values())
        if not run_id or is_placeholder(run_id):
            continue
        if is_non_run_reference_id(run_id):
            checked_rows += 1
            if status in {"pass", "passed", "ok", "success"} and not has_run_manifest_reference(combined):
                errors.append(
                    f"Run Evidence row uses non-run reference `{run_id}` as run_id; move it to commit_ref/push_ref/source_ref notes or provide a run manifest"
                )
        ref = wr.parse_evidence_ref(run_id)
        if ref and ref.ref_type != "run":
            checked_rows += 1
            errors.append(
                f"Run Evidence run_id `{run_id}` is a typed {ref.ref_type} reference; use a real run id or move the reference to manifest/artifact/notes"
            )

    for row in extract_table(progress_text, "## Final Evidence Ledger"):
        acceptance_id = clean(row.get("acceptance_id", "<unknown>"))
        if acceptance_id.lower() in {"", "not-needed", "待填写"}:
            continue
        final_status = clean(row.get("final_status", "")).upper()
        combined = " ".join(clean(value) for value in row.values())
        if final_status != "PASS" or not COMMAND_EVIDENCE_SIGNAL_RE.search(combined):
            continue
        if has_typed_non_run_reference(combined) and not has_run_manifest_reference(combined):
            checked_rows += 1
            errors.append(
                f"ledger {acceptance_id}: command PASS cannot rely only on commit/source/artifact typed refs; add .agent-state/runs/<run_id>/manifest.json"
            )

    for row in extract_table(progress_text, "## Acceptance Evidence"):
        acceptance_id = clean(row.get("acceptance_id", "<unknown>"))
        if acceptance_id.lower() in {"", "not-needed", "待填写"}:
            continue
        status = clean(row.get("status", "") or row.get("final_status", "")).upper()
        if status != "PASS":
            continue
        combined = " ".join(clean(value) for value in row.values())
        if not COMMAND_EVIDENCE_SIGNAL_RE.search(combined):
            continue
        if has_typed_non_run_reference(combined) and not has_run_manifest_reference(combined):
            checked_rows += 1
            errors.append(
                f"Acceptance Evidence {acceptance_id}: command PASS cannot rely only on "
                "commit/source/artifact typed refs; add .agent-state/runs/<run_id>/manifest.json"
            )
    return {"status": "pass" if not errors else "fail", "checked_rows": checked_rows, "errors": errors}


def repo_relative_path(root: Path, value: str) -> tuple[Path | None, str | None]:
    cleaned = clean(value)
    if is_placeholder(cleaned) or is_not_needed_like(cleaned):
        return None, "path is missing"
    candidate = Path(cleaned)
    if candidate.is_absolute():
        return None, "path must be project-root relative"
    if ".." in candidate.parts:
        return None, "path must not contain .."
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None, "path must stay under project root"
    return resolved, None


def denied_source_root_part(root: Path, path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "outside-project-root"
    wrapped = f"/{rel}/"
    for denied in SOURCE_ROOT_DENIED_PARTS:
        if rel == denied or rel.startswith(f"{denied}/") or f"/{denied}/" in wrapped:
            return denied
    return None


def git_worktree_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "inside_work_tree": False,
        "dirty_count": None,
        "head": None,
        "top_level": None,
    }
    try:
        inside = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return info
    if inside.returncode != 0 or clean(inside.stdout).lower() != "true":
        return info
    info["inside_work_tree"] = True
    for key, command in (
        ("top_level", ["git", "-C", str(path), "rev-parse", "--show-toplevel"]),
        ("head", ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"]),
    ):
        try:
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            info[key] = clean(result.stdout.splitlines()[0] if result.stdout.splitlines() else "")
    try:
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--short"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return info
    if status.returncode == 0:
        info["dirty_count"] = len([line for line in status.stdout.splitlines() if line.strip()])
    return info


def source_root_rows_from_registry(root: Path) -> list[dict[str, str]]:
    conventions = root / ".agents" / "references" / "project-conventions.md"
    if not conventions.is_file():
        return []
    return extract_table(read_text(conventions), "## Source Root Registry")


def real_source_root_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    real: list[dict[str, str]] = []
    for row in rows:
        root_id = clean(row.get("root_id", "") or row.get("id", ""))
        source_root = clean(row.get("source_root", "") or row.get("path", ""))
        status = clean(row.get("status", "")).lower()
        if is_placeholder(root_id) or is_placeholder(source_root) or is_not_needed_like(root_id) or is_not_needed_like(source_root):
            continue
        if status in {"not-needed", "not needed"}:
            continue
        real.append(row)
    return real


def source_roots_closeout_check(root: Path, progress_text: str, strict_required: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    progress_rows = real_source_root_rows(extract_table(progress_text, "## Source Roots / Repos Touched"))
    registry_rows = real_source_root_rows(source_root_rows_from_registry(root))
    root_git = git_worktree_info(root)
    if strict_required and not root_git["inside_work_tree"] and not progress_rows:
        errors.append(
            "strict closeout project root is not a git worktree; declare Source Roots / Repos Touched for every touched source root"
        )
    if progress_rows and not registry_rows:
        warnings.append("Source Roots / Repos Touched exists but Source Root Registry is missing from .agents/references/project-conventions.md")

    checked_roots: list[dict[str, Any]] = []
    for row in progress_rows:
        root_id = clean(row.get("root_id", "") or row.get("id", ""))
        source_root_value = clean(row.get("source_root", "") or row.get("path", ""))
        vcs_root_value = clean(row.get("vcs_root", "")) or source_root_value
        status = clean(row.get("status", "")).lower()
        dirty_status = clean(row.get("dirty_status", "")).lower()
        evidence = clean(row.get("evidence_manifest", "") or row.get("evidence", "") or row.get("manifest", ""))
        source_path, source_error = repo_relative_path(root, source_root_value)
        vcs_path, vcs_error = repo_relative_path(root, vcs_root_value)
        if source_error or source_path is None:
            errors.append(f"Source Roots / Repos Touched {root_id}: invalid source_root `{source_root_value}` ({source_error})")
            continue
        denied = denied_source_root_part(root, source_path)
        if denied:
            errors.append(f"Source Roots / Repos Touched {root_id}: source_root points at generated/runtime/archive path `{denied}`")
        if not source_path.exists():
            errors.append(f"Source Roots / Repos Touched {root_id}: source_root does not exist: {source_root_value}")
        if vcs_error or vcs_path is None:
            errors.append(f"Source Roots / Repos Touched {root_id}: invalid vcs_root `{vcs_root_value}` ({vcs_error})")
            vcs_path = source_path
        git_info = git_worktree_info(vcs_path)
        checked_roots.append(
            {
                "root_id": root_id,
                "source_root": source_root_value,
                "vcs_root": vcs_root_value,
                "inside_work_tree": git_info["inside_work_tree"],
                "dirty_count": git_info["dirty_count"],
                "head": git_info["head"],
                "status": status,
                "dirty_status": dirty_status or "<missing>",
                "evidence_manifest": evidence or "<missing>",
            }
        )
    return {
        "status": "pass" if not errors else "fail",
        "root_git": root_git,
        "progress_rows": len(progress_rows),
        "registry_rows": len(registry_rows),
        "checked_roots": checked_roots,
        "errors": errors,
        "warnings": warnings,
    }


def validate(
    root: Path,
    task_plan_path: Path,
    progress_path: Path,
    findings_path: Path | None,
    strict_trigger: bool,
    require_existing_artifacts: bool,
    archives: list[Path],
    require_archive: bool,
    check_template: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if (is_template_path(task_plan_path) or is_template_path(progress_path)) and not check_template:
        return {
            "status": "skipped",
            "reason": "raw templates are placeholders; use --check-template to validate template examples",
            "errors": [],
            "warnings": [],
            "checks": {},
        }

    if not task_plan_path.is_file():
        return {"status": "fail", "errors": [f"task plan not found: {task_plan_path}"], "warnings": [], "checks": {}}
    if not progress_path.is_file():
        return {"status": "fail", "errors": [f"progress not found: {progress_path}"], "warnings": [], "checks": {}}

    task_plan_text = read_text(task_plan_path)
    progress_text = read_text(progress_path)
    findings_text = read_text(findings_path) if findings_path and findings_path.is_file() else None
    standard_state_paths = (
        task_plan_path == root / "task_plan.md"
        and progress_path == root / "progress.md"
        and findings_path == root / "findings.md"
    )
    snapshot = task_snapshot.load_current_task_snapshot(root) if standard_state_paths else None
    if snapshot is not None:
        checks["current_task_snapshot"] = asdict(snapshot)
    tier = snapshot.risk_tier if snapshot is not None and snapshot.risk_tier else risk_tier(task_plan_text)
    external_scope = has_external_scope(task_plan_text)
    release_artifact_signal = has_release_artifact_signal(task_plan_text, progress_text)
    strict_required = strict_trigger or tier in {"high", "release"} or external_scope

    if not strict_required:
        checks: dict[str, Any] = {}
        errors: list[str] = []
        scripts = scripts_dir(root)
        warnings.append("risk tier / impact scope do not require fail-closed closeout; focused validation is enough")
        skill_curator_check, skill_curator_errors = validate_referenced_skill_curator_reports(
            root,
            scripts,
            task_plan_text,
            progress_text,
            findings_text,
            require_existing_artifacts=False,
        )
        if skill_curator_check.get("paths"):
            checks["referenced_skill_curator_reports"] = skill_curator_check
            errors.extend(skill_curator_errors)
        workflow_value_check, workflow_value_errors = validate_referenced_workflow_value_reports(
            root,
            task_plan_text,
            progress_text,
            findings_text,
        )
        if workflow_value_check.get("paths"):
            checks["referenced_workflow_value_reports"] = workflow_value_check
            errors.extend(workflow_value_errors)
        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "warnings": warnings,
            "risk_tier": tier,
            "external_scope": external_scope,
            "release_artifact_signal": release_artifact_signal,
            "strict_required": False,
            "checks": checks,
        }

    active_ids = validate_active_ids(
        task_plan_text,
        progress_text,
        findings_text,
        strict=True,
        snapshot=snapshot,
    )
    checks["active_task_id"] = active_ids
    errors.extend(active_ids["errors"])

    active_lifecycle = active_lifecycle_closeout_check(
        progress_text,
        require_closeout_state=True,
        snapshot_lifecycle_state=snapshot.lifecycle_state if snapshot is not None else None,
    )
    checks["active_lifecycle_closeout"] = active_lifecycle
    errors.extend(active_lifecycle["errors"])

    ledger_status = final_ledger_status_check(progress_text)
    checks["final_ledger_closeout_status"] = ledger_status
    errors.extend(ledger_status["errors"])

    typed_evidence_refs = typed_reference_evidence_check(progress_text)
    checks["typed_evidence_refs"] = typed_evidence_refs
    errors.extend(typed_evidence_refs["errors"])

    source_roots = source_roots_closeout_check(
        root,
        progress_text,
        strict_required=strict_required,
    )
    checks["source_roots_closeout"] = source_roots
    errors.extend(source_roots["errors"])
    warnings.extend(source_roots["warnings"])

    next_action_errors = validate_next_action_quality(progress_text)
    checks["next_action_quality"] = {"status": "pass" if not next_action_errors else "fail", "errors": next_action_errors}
    errors.extend(next_action_errors)

    scripts = scripts_dir(root)
    base = [sys.executable]
    common = ["--root", str(root), "--task-plan", str(task_plan_path), "--progress", str(progress_path), "--strict-trigger", "--format", "json"]
    validators: list[tuple[str, list[str]]] = [
        ("traceability", base + [str(scripts / "validate-traceability.py"), *common]),
    ]
    if re.search(r"(?im)^## +Workflow Trace\s*$", progress_text):
        validators.append(("workflow_trace", base + [str(scripts / "validate-workflow-trace-consistency.py"), *common]))
    validators.extend([
        (
            "evidence_waivers",
            base
            + [
                str(scripts / "validate-evidence-waivers.py"),
                "--root",
                str(root),
                "--task-plan",
                str(task_plan_path),
                "--progress",
                str(progress_path),
                "--strict-trigger",
                "--format",
                "json",
                *(["--require-existing-artifacts"] if require_existing_artifacts else []),
            ],
        ),
        ("review_authorization", base + [str(scripts / "validate-review-authorization.py"), *common]),
    ])
    if wr.reviewer_route_requested(progress_text):
        validators.append(
            ("reviewer_assessment", base + [str(scripts / "validate-reviewer-assessment.py"), *common]),
        )
    validators.append(
        (
            "claim_evidence",
            base
            + [
                str(scripts / "validate-claim-evidence.py"),
                "--root",
                str(root),
                "--progress",
                str(progress_path),
                "--format",
                "json",
            ],
        )
    )

    if (tier == "release" or external_scope) and release_artifact_signal:
        validators.append(
            ("release_artifact_source", base + [str(scripts / "validate-release-artifact-source.py"), *common])
        )

    checks["fact_domain_execution"] = run_fact_domain_validators_once(validators, root, checks, errors)

    boundary_artifacts, boundary_errors = external_content_boundary_artifacts(task_plan_text, progress_text)
    checks["external_content_boundary"] = {"artifacts": boundary_artifacts, "status": "pass" if not boundary_errors else "fail"}
    errors.extend(boundary_errors)
    for artifact in boundary_artifacts:
        command = [
            sys.executable,
            str(scripts / "validate-external-content-boundary.py"),
            "--root",
            str(root),
            "--input",
            artifact,
            "--format",
            "json",
        ]
        result = run_validator(f"external_content_boundary:{artifact}", command, root)
        checks[f"external_content_boundary:{artifact}"] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            checks["external_content_boundary"]["status"] = "fail"
            errors.append(f"external content boundary validator failed: {artifact}")

    ui_browser_required = tier == "release" and release_ui_browser_signal(task_plan_text, progress_text)
    checks["browser_ui_evidence"] = {
        "required": ui_browser_required,
        "status": "pass",
    }
    ui_browser_present, ui_browser_errors = browser_ui_evidence_present(
        root,
        progress_text,
        require_existing_artifacts if ui_browser_required else False,
    )
    checks["browser_ui_evidence"]["present"] = ui_browser_present
    if ui_browser_required:
        errors.extend(ui_browser_errors)
        if not ui_browser_present:
            checks["browser_ui_evidence"]["status"] = "fail"
            errors.append("release UI/browser change requires Browser / UI Evidence row or matching Verification Waiver")

    packet_paths = referenced_role_review_packets(progress_text)
    packet_result_required = packets_requiring_role_review_result(progress_text, packet_paths)
    checks["referenced_role_review_packets"] = {"paths": packet_paths, "status": "pass"}
    for packet_path in packet_paths:
        packet_rel = packet_path.rstrip("/")
        if require_existing_artifacts and not (root / packet_rel).is_dir():
            checks["referenced_role_review_packets"]["status"] = "fail"
            errors.append(f"referenced role review packet is missing: {packet_rel}")
            continue
        command = [
            sys.executable,
            str(scripts / "validate-role-review-packet.py"),
            "--root",
            str(root),
            "--packet",
            packet_rel,
            "--format",
            "json",
        ]
        if tier in {"high", "release"}:
            command.extend(["--risk-tier", tier])
        if packet_rel in packet_result_required:
            command.append("--require-result")
        result = run_validator(f"role_review_packet:{packet_rel}", command, root)
        checks[f"role_review_packet:{packet_rel}"] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            checks["referenced_role_review_packets"]["status"] = "fail"
            errors.append(f"role review packet validator failed: {packet_rel}")

    campaign_paths = referenced_dynamic_agent_campaigns(progress_text)
    checks["referenced_dynamic_agent_campaigns"] = {"paths": campaign_paths, "status": "pass"}
    for campaign_path in campaign_paths:
        if require_existing_artifacts and not (root / campaign_path).is_dir():
            checks["referenced_dynamic_agent_campaigns"]["status"] = "fail"
            errors.append(f"referenced dynamic agent campaign is missing: {campaign_path}")
            continue
        command = [
            sys.executable,
            str(scripts / "validate-dynamic-agent-campaign.py"),
            "--root",
            str(root),
            "--campaign",
            campaign_path,
            "--format",
            "json",
        ]
        result = run_validator(f"dynamic_agent_campaign:{campaign_path}", command, root)
        checks[f"dynamic_agent_campaign:{campaign_path}"] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            checks["referenced_dynamic_agent_campaigns"]["status"] = "fail"
            errors.append(f"dynamic agent campaign validator failed: {campaign_path}")

    skill_curator_check, skill_curator_errors = validate_referenced_skill_curator_reports(
        root,
        scripts,
        task_plan_text,
        progress_text,
        findings_text,
        require_existing_artifacts=require_existing_artifacts,
    )
    if skill_curator_check.get("paths"):
        checks["referenced_skill_curator_reports"] = skill_curator_check
        errors.extend(skill_curator_errors)

    workflow_value_check, workflow_value_errors = validate_referenced_workflow_value_reports(
        root,
        task_plan_text,
        progress_text,
        findings_text,
    )
    if workflow_value_check.get("paths"):
        checks["referenced_workflow_value_reports"] = workflow_value_check
        errors.extend(workflow_value_errors)

    run_ids = sorted(
        set(evidence_referenced_run_ids(task_plan_text, progress_text, findings_text))
        | set(structured_run_ids(task_plan_text))
        | set(structured_run_ids(progress_text))
        | set(referenced_run_evidence_ids(progress_text))
    )
    checks["referenced_run_manifests"] = {"run_ids": run_ids, "status": "pass"}
    for run_id in run_ids:
        command = [
            sys.executable,
            str(scripts / "validate-run-manifest.py"),
            "--root",
            str(root),
            "--run",
            run_id,
            "--strict-current",
            "--format",
            "json",
            *(["--require-existing-artifacts"] if require_existing_artifacts else []),
        ]
        result = run_validator(f"run_manifest:{run_id}", command, root)
        checks[f"run_manifest:{run_id}"] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            checks["referenced_run_manifests"]["status"] = "fail"
            errors.append(f"referenced run manifest failed: {run_id}")

    archive_paths = archives
    if require_archive and not archive_paths:
        errors.append("--require-archive requires at least one --archive path")
    for archive in archive_paths:
        command = [
            sys.executable,
            str(scripts / "validate-task-archive-hygiene.py"),
            "--root",
            str(root),
            "--archive",
            str(archive),
            "--strict-new",
            "--format",
            "json",
        ]
        result = run_validator(f"archive:{archive}", command, root)
        checks[f"archive:{archive}"] = {
            "status": result["status"],
            "returncode": result["returncode"],
            "details": result["json"] if result["json"] is not None else result["stdout"],
        }
        if result["status"] != "pass":
            errors.append(f"archive hygiene failed: {archive}")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "risk_tier": tier,
        "external_scope": external_scope,
        "release_artifact_signal": release_artifact_signal,
        "strict_required": strict_required,
        "require_existing_artifacts": require_existing_artifacts,
        "checks": checks,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-closed closeout validator for high/release/external-system explicit closeout. Orchestrates remaining closeout fact domains only; knowledge-promotion and doc-fact-drift stay independently invokable."
    )
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan markdown file.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--findings", default="findings.md", help="Findings markdown file.")
    parser.add_argument("--strict-trigger", action="store_true", help="Force fail-closed closeout checks even outside high/release/external-system.")
    parser.add_argument("--require-existing-artifacts", action="store_true", help="Require repo-local evidence paths in ledger and referenced run manifests to exist.")
    parser.add_argument("--archive", action="append", default=[], help="Completed task archive to validate. May be repeated.")
    parser.add_argument("--require-archive", action="store_true", help="Require at least one --archive and validate it strictly.")
    parser.add_argument("--check-template", action="store_true", help="Validate raw templates intentionally.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"risk_tier: {payload.get('risk_tier', 'unknown')}")
    print(f"external_scope: {str(payload.get('external_scope', False)).lower()}")
    print(f"strict_required: {str(payload.get('strict_required', False)).lower()}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")
    for error in payload.get("errors", []):
        print(f"error: {error}")
    for name, check in (payload.get("checks") or {}).items():
        if isinstance(check, dict) and "status" in check:
            print(f"check: {name}: {check['status']}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    task_plan = Path(args.task_plan)
    progress = Path(args.progress)
    findings = Path(args.findings) if args.findings else None
    if not task_plan.is_absolute():
        task_plan = root / task_plan
    if not progress.is_absolute():
        progress = root / progress
    if findings is not None and not findings.is_absolute():
        findings = root / findings
    archives = [Path(item) for item in args.archive]

    payload = validate(
        root=root,
        task_plan_path=task_plan,
        progress_path=progress,
        findings_path=findings,
        strict_trigger=args.strict_trigger,
        require_existing_artifacts=args.require_existing_artifacts,
        archives=archives,
        require_archive=args.require_archive,
        check_template=args.check_template,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
