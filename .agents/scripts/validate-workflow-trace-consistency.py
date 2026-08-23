#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc
import workflow_routing as wr


ROOT_STATE_FORBIDDEN = {
    "agent-debug-packet.json",
    "agent-debug-packet.md",
    "agent-view-debug.json",
    "agent-view-debug.md",
    "agent-view-debug-packet.json",
    "agent-view-debug-packet.md",
    "debug-packet.json",
    "debug-packet.md",
    "workflow_trace.json",
    "workflow-trace.json",
    "workflow-debug.json",
    "workflow-debug.md",
    "workflow-plan.json",
    "workflow-run.json",
}

ROOT_STATE_FORBIDDEN_DIRS = {
    "agent-debug-packet",
    "agent-view-debug",
    "agent-view-debug-packet",
    "debug-packet",
    "workflow-debug",
}

PLACEHOLDERS = {
    "",
    "none",
    "n/a",
    "na",
    "not-needed",
    "not needed",
    "unknown",
    "optional",
    "todo",
    "tbd",
    "待填写",
    "missing",
    "pending",
    "required",
}

NOT_RUN_STATUSES = {
    "not-needed",
    "not-used",
    "none",
    "missing",
    "unavailable",
    "skipped",
    "optional",
    "not-run",
}
STALE_TRACE_STATUSES = {"planned", "pending", "todo", "not-run", "not run", "待运行", "计划中"}
PASS_TRACE_STATUSES = {"pass", "passed", "done", "complete", "completed", "yes"}

POLICY_AUTO_SKIP_STATUSES = {
    "not-authorized",
    "no-authorization",
    "no-user-authorization",
    "user-not-authorized",
}

IMPLEMENTATION_PATTERNS = [
    r"\bimplemented\b",
    r"\bpatched\b",
    r"\bmodified\b",
    r"\bsource change\b",
    r"\bcode changed\b",
    r"\bcommit\b",
    r"\bpush\b",
    r"\bdeploy(?:ed|ment)?\b",
    r"\bdb write\b",
    r"\bmigration\b",
    r"\bpytest\b",
    r"\btests?\b",
    r"\bsmoke\b",
    r"\bbuild\b",
    r"已实现",
    r"已修复",
    r"改代码",
    r"写入",
    r"提交",
    r"推送",
    r"部署",
    r"迁移",
    r"测试",
]

EXTERNAL_REVIEWER_PATTERNS = [
    r"\bgemini\b",
    r"\bclaude\b",
    r"\bexternal\b",
    r"外部",
    r"第三方",
]

ARTIFACT_PATTERNS = [
    r"\bjar\b",
    r"\b(?:docker|container)\s+image\b",
    r"\b(?:dist|release|deploy(?:ment)?|build)\b.{0,32}\b(?:package|bundle|artifact|image)\b",
    r"\b(?:dist|release|deploy|deployment|build)[\w./-]*\.(?:zip|tar\.gz|jar)\b",
    r"部署包",
    r"发布包",
    r"构建产物",
    r"镜像",
]


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("/", "_")


def normalize_status(value: str) -> str:
    return clean_cell(value).lower().strip()


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def is_placeholder(value: str, *, allow_not_needed: bool = False) -> bool:
    normalized = clean_cell(value).lower()
    if allow_not_needed and normalized in {"none", "not-needed"}:
        return False
    return (
        normalized in PLACEHOLDERS
        or "待填写" in normalized
        or "<run_id>" in normalized
        or normalized.startswith("optional /")
    )


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


def section_text(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading))


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=False,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def parse_key_value_table(markdown_text: str, heading: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in extract_table(markdown_text, heading):
        key = normalize_key(row.get("item", "") or row.get("field", "") or row.get("check", ""))
        value = row.get("value", "")
        if key:
            values[key] = value
    return values


def workflow_rows(progress_text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for row in extract_table(progress_text, "## Workflow Trace"):
        step = normalize_key(row.get("step", ""))
        if step:
            rows[step] = row
    return rows


def contains_any(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def risk_tier(task_plan_text: str) -> str:
    return wr.risk_tier_or_unknown(task_plan_text)


def has_external_scope(task_plan_text: str) -> bool:
    return wr.has_external_system_scope(task_plan_text)


def has_release_artifact_signal(task_plan_text: str, progress_text: str) -> bool:
    haystack = f"{task_plan_text}\n{progress_text}".lower()
    return bool(contains_any(haystack, ARTIFACT_PATTERNS))


def status_is_stale(value: str) -> bool:
    return normalize_status(value).replace("_", "-") in STALE_TRACE_STATUSES


def status_is_pass(value: str) -> bool:
    return normalize_status(value).replace("_", "-") in PASS_TRACE_STATUSES


def ship_check_records_delivery_decision(ship_text: str) -> bool:
    delivery_lines = [
        line
        for line in ship_text.splitlines()
        if re.search(r"\b(delivery|ship|handoff|release)\b", line, flags=re.IGNORECASE)
        or "交付" in line
        or "发布" in line
    ]
    selected = "\n".join(delivery_lines) if delivery_lines else ship_text
    normalized = selected.lower()
    if "不可交付" in selected or "不能交付" in selected or "禁止交付" in selected:
        return False
    sanitized = re.sub(r"\bno blockers?\b", "", normalized)
    sanitized = re.sub(r"\bfail(?:ures)?\s*=\s*0\b", "", sanitized)
    if re.search(r"\b(no|blocked|fail|failed|not[- ]ready)\b", sanitized):
        return False
    if re.search(r"\b(pass|yes|ready)\b", sanitized) or "可以交付" in selected or "可交付" in selected:
        return True
    return False


def run_evidence_haystack(row: dict[str, str]) -> str:
    keys = (
        "run_id",
        "trace_id",
        "command",
        "command___check",
        "command_check",
        "tool___command",
        "tool_command",
        "result",
        "conclusion",
        "exit_code",
        "manifest___artifact",
        "manifest_artifact",
        "artifact",
        "notes",
    )
    return " ".join(row.get(key, "") for key in keys).lower()


def run_evidence_status(row: dict[str, str]) -> str:
    for key in ("status", "result", "conclusion"):
        value = row.get(key, "")
        if value:
            return value
    if row.get("exit_code", "").strip() == "0":
        return "pass"
    return ""


def row_status(rows: dict[str, dict[str, str]], step: str) -> str:
    return normalize_status(rows.get(step, {}).get("status", ""))


def row_evidence(rows: dict[str, dict[str, str]], step: str) -> str:
    return rows.get(step, {}).get("evidence", "")


def provider_includes_codegraph(provider: str) -> bool:
    normalized = normalize_status(provider)
    return "codegraph" in normalized or normalized == "both"


def source_confirmed_yes(value: str) -> bool:
    normalized = normalize_status(value)
    return normalized in {"yes", "true", "source-confirmed", "confirmed", "已确认"}


def evidence_has_source_confirmed_yes(value: str) -> bool:
    normalized = value.lower()
    return bool(
        re.search(r"source_confirmed\s*=\s*(yes|true)", normalized)
        or re.search(r"source confirmed\s*[:=]\s*(yes|true)", normalized)
        or re.search(r"源码确认\s*[:：]?\s*(yes|true|已确认)", normalized)
    )


def codegraph_pilot_effect_present(progress_text: str) -> bool:
    metric_fields = (
        "decision_changed",
        "elapsed_or_saved_time",
        "artifact_size_or_cost",
        "root_freshness",
        "freshness_basis",
        "roi_signal",
        "roi_claim_status",
        "reindexrecommended",
    )
    for row in extract_table(progress_text, "## Structural Index Pilot Effect"):
        provider = normalize_status(row.get("provider", ""))
        decision = normalize_status(row.get("decision", ""))
        if not provider_includes_codegraph(provider) and "codegraph" not in decision:
            continue
        if decision != "trial-index-codegraph":
            continue
        if not all(not is_placeholder(row.get(field, "")) for field in metric_fields):
            continue
        if not source_confirmed_yes(row.get("source_confirmed", "")):
            continue
        roi_claim_status = normalize_status(row.get("roi_claim_status", ""))
        if roi_claim_status not in {"not-claimed", "candidate", "proven-positive", "neutral", "negative"}:
            continue
        reindex_recommended = normalize_status(row.get("reindexrecommended", ""))
        if reindex_recommended not in {"yes", "no", "unknown", "not-needed"}:
            continue
        disposition = normalize_status(row.get("disposition", ""))
        if disposition not in {"useful", "neutral", "costly", "defer"}:
            continue
        return True
    return False


def status_requires_evidence(status: str) -> bool:
    status = normalize_status(status)
    if not status or status in NOT_RUN_STATUSES or "/" in status:
        return False
    return True


def load_trace_artifact(
    root: Path,
    trace_artifact: str | None,
    progress_text: str,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any] | None:
    if not trace_artifact:
        return None
    artifact_path = Path(trace_artifact)
    if not artifact_path.is_absolute():
        artifact_path = root / artifact_path
    try:
        relative = artifact_path.resolve().relative_to((root / ".agent-state" / "runs").resolve())
    except ValueError:
        errors.append("Trace artifact must live under .agent-state/runs/<run_id>/ and remain a derived artifact, not a root state file.")
        return None
    if not artifact_path.exists():
        errors.append(f"Trace artifact is missing: {artifact_path}")
        return None
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Trace artifact is not valid JSON: {artifact_path}: {exc}")
        return None

    missing = [field for field in ("derived_from", "run_id", "source_sha256") if is_placeholder(str(data.get(field, "")))]
    if missing:
        errors.append(f"Trace artifact is missing derived metadata fields: {', '.join(missing)}")
    source_sha = str(data.get("source_sha256", ""))
    if source_sha and not re.fullmatch(r"[a-fA-F0-9]{64}", source_sha):
        errors.append("Trace artifact source_sha256 must be a 64-character hex digest.")
    derived_from = str(data.get("derived_from", ""))
    if derived_from == "progress.md#Workflow Trace" and re.fullmatch(r"[a-fA-F0-9]{64}", source_sha):
        workflow_trace_text = section_text(progress_text, "## Workflow Trace").encode("utf-8")
        actual_sha = hashlib.sha256(workflow_trace_text).hexdigest()
        if actual_sha.lower() != source_sha.lower():
            errors.append("Trace artifact source_sha256 does not match progress.md#Workflow Trace.")
    elif derived_from and "workflow trace" not in derived_from.lower():
        errors.append("Trace artifact derived_from must point to progress.md#Workflow Trace or an equivalent Workflow Trace section.")
    if str(data.get("source_of_truth", "")).lower() in {"true", "yes", "authoritative"}:
        errors.append("Trace artifact must not declare itself as source of truth.")
    if not str(relative):
        warnings.append("Trace artifact path was accepted under .agent-state/runs.")
    return data


def validate(
    root: Path,
    task_plan_path: Path,
    progress_path: Path,
    trace_artifact: str | None = None,
    check_template: bool = False,
    strict_trigger: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if (is_template_path(task_plan_path) or is_template_path(progress_path)) and not check_template:
        return {
            "status": "skipped",
            "reason": "raw templates are placeholders; use --check-template to validate template examples",
            "errors": [],
            "warnings": [],
        }

    for forbidden in ROOT_STATE_FORBIDDEN:
        if (root / forbidden).exists():
            errors.append(f"Root-level {forbidden} is forbidden; workflow trace artifacts must stay under .agent-state/runs/<run_id>/")
    for forbidden in ROOT_STATE_FORBIDDEN_DIRS:
        if (root / forbidden).is_dir():
            errors.append(f"Root-level {forbidden}/ is forbidden; workflow trace artifacts must stay under .agent-state/runs/<run_id>/")

    if not task_plan_path.exists():
        errors.append(f"Task plan not found: {task_plan_path}")
        task_plan_text = ""
    else:
        task_plan_text = task_plan_path.read_text(encoding="utf-8")
    if not progress_path.exists():
        errors.append(f"Progress file not found: {progress_path}")
        progress_text = ""
    else:
        progress_text = progress_path.read_text(encoding="utf-8")

    trace_data = load_trace_artifact(root, trace_artifact, progress_text, errors, warnings)

    rows = workflow_rows(progress_text)
    has_trace_heading = bool(re.search(r"(?im)^## +Workflow Trace\s*$", progress_text))
    if strict_trigger and has_trace_heading and not rows:
        errors.append("Workflow Trace heading is present but has no rows.")
    if not has_trace_heading:
        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "warnings": warnings + ["Workflow Trace omitted; Validation / Acceptance Evidence / run manifest remain the evidence owners."],
            "trace_present": False,
        }

    for step, row in rows.items():
        status = normalize_status(row.get("status", ""))
        evidence = row.get("evidence", "")
        if status_requires_evidence(status) and is_placeholder(evidence):
            errors.append(f"Workflow Trace step '{step}' status '{status}' requires non-placeholder evidence.")

    run_evidence_rows = extract_table(progress_text, "## Run Evidence")
    for step, row in rows.items():
        status = normalize_status(row.get("status", ""))
        if not status_is_stale(status):
            continue
        for evidence_row in run_evidence_rows:
            haystack = run_evidence_haystack(evidence_row)
            evidence_status = run_evidence_status(evidence_row)
            if step.replace("_", "-").lower() in haystack.replace("_", "-") and status_is_pass(evidence_status):
                errors.append(
                    f"Workflow Trace step '{step}' remains {status} while Run Evidence records {evidence_status}; update Workflow Trace before closeout."
                )
                break
        if step == "ship-check" and status_is_stale(status):
            ship_text = section_text(progress_text, "## Ship Check")
            if ship_check_records_delivery_decision(ship_text):
                errors.append("Workflow Trace step 'ship-check' remains planned/pending while Ship Check records a delivery decision.")

    review_boundary = parse_key_value_table(progress_text, "## Review / Audit Boundary")
    boundary_mode = normalize_status(review_boundary.get("mode", ""))
    if boundary_mode in {"review-only", "plan-only"}:
        selected = "\n\n".join(
            section_text(progress_text, heading)
            for heading in (
                "## Completed",
                "## In Progress",
                "## Run Evidence",
                "## Validation",
                "## Changed Files Manifest",
                "## Diff-to-Plan",
            )
        )
        hits = contains_any(selected, IMPLEMENTATION_PATTERNS)
        if hits:
            errors.append(f"{boundary_mode} Workflow Trace is inconsistent with implementation/write evidence in progress.md.")

    isolated_status = row_status(rows, "isolated_reviewer")
    isolated_evidence = row_evidence(rows, "isolated_reviewer")
    isolated = parse_key_value_table(progress_text, "## Isolated Reviewer")
    start_result = normalize_status(isolated.get("start_result", ""))
    auth_scope = normalize_status(isolated.get("authorization_scope", ""))
    reviewer_tool = isolated.get("reviewer_tool", "")
    packet_status = normalize_status(isolated.get("packet_validator_status", ""))
    packet_artifact = isolated.get("packet_validator_artifact", "")
    isolated_reason = isolated.get("reason", "")
    isolated_combined = f"{isolated_status}\n{isolated_evidence}\n{start_result}\n{isolated_reason}".lower()

    trace_policy_auto_started = "policy-auto-started" in isolated_status
    if trace_policy_auto_started:
        if "started" not in start_result:
            errors.append("Workflow Trace says policy-auto reviewer started, but Isolated Reviewer Start result is not a started value.")
        if packet_status != "pass":
            errors.append("Policy-auto started reviewer requires Packet validator status = pass.")
        if is_placeholder(packet_artifact):
            errors.append("Policy-auto started reviewer requires a non-placeholder Packet validator artifact.")
        summary_rows = extract_table(progress_text, "## Role Review Summary")
        if not summary_rows:
            errors.append("Policy-auto started reviewer requires Role Review Summary with main Codex disposition.")

    if auth_scope == "policy-auto" and "started" in start_result and contains_any(reviewer_tool, EXTERNAL_REVIEWER_PATTERNS):
        errors.append("External model reviewer cannot start under policy-auto without external-standing-opt-in.")

    if "policy-auto-started" in isolated_status and is_placeholder(isolated_evidence):
        errors.append("Workflow Trace isolated_reviewer policy-auto-started requires packet / validator / verdict evidence.")

    release_like_task = risk_tier(task_plan_text) == "release" or has_external_scope(task_plan_text)
    if release_like_task and auth_scope == "policy-auto":
        if any(status in isolated_combined for status in POLICY_AUTO_SKIP_STATUSES):
            errors.append("Policy-auto reviewer cannot be skipped as not-authorized/no user authorization in Workflow Trace.")
    if release_like_task and any(status in isolated_combined for status in POLICY_AUTO_SKIP_STATUSES):
        errors.append("Release/external-system Workflow Trace cannot use not-authorized/no user authorization to skip internal policy-auto reviewer assessment.")

    release_gate = parse_key_value_table(progress_text, "## Release Artifact Source Gate")
    source_required = normalize_status(release_gate.get("required", ""))
    source_mode = normalize_status(release_gate.get("source_mode", ""))
    release_trace_status = row_status(rows, "release_artifact_source_gate")
    release_trace_evidence = row_evidence(rows, "release_artifact_source_gate")
    release_gate_required = source_required == "yes" or (
        source_mode and source_mode not in {"not-needed", "no", "none"} and "/" not in source_mode
    )
    release_signal = risk_tier(task_plan_text) == "release" or has_external_scope(task_plan_text)
    release_signal = release_signal and has_release_artifact_signal(task_plan_text, progress_text)
    if release_gate_required and release_trace_status in {"", "not-needed", "missing", "not-run"}:
        errors.append("Release Artifact Source Gate is required but Workflow Trace marks release_artifact_source_gate as missing/not-needed.")
    if release_signal and release_trace_status in {"", "not-needed", "missing", "not-run"}:
        errors.append("Release/external-system artifact signal requires release_artifact_source_gate in Workflow Trace.")
    if release_trace_status in (wr.RELEASE_SOURCE_MODES - {"not-needed"}) and is_placeholder(release_trace_evidence):
        errors.append("Workflow Trace release_artifact_source_gate requires release-source packet / artifact evidence.")

    structural_index_steps = ("graphify", "codegraph", "structural_index")
    codegraph_trial_authorized = False
    for structural_step in structural_index_steps:
        structural_status = row_status(rows, structural_step)
        structural_evidence = row_evidence(rows, structural_step)
        evidence_lower = structural_evidence.lower()
        if structural_status == "refresh-and-query":
            display = "Structural Index" if structural_step == "structural_index" else structural_step
            if not re.search(r"explicit|user|approved|授权|用户", evidence_lower):
                errors.append(f"{display} refresh-and-query requires explicit user authorization evidence.")
            if re.search(r"auto\s*hook|default|自动\s*hook|默认", evidence_lower):
                errors.append(f"{display} refresh-and-query must not be caused by default hooks or automatic refresh/indexing.")
            if structural_step == "codegraph":
                errors.append("CodeGraph must use trial-index-codegraph for explicit indexing; refresh-and-query is Graphify-only.")
            if structural_step == "structural_index" and re.search(r"\bcodegraph\b|\.codegraph", evidence_lower):
                errors.append("CodeGraph structural index indexing must not be caused by default hooks or automatic refresh/indexing.")
        if structural_status == "trial-index-codegraph":
            if not re.search(r"explicit|user|approved|授权|用户", evidence_lower):
                errors.append("CodeGraph trial-index-codegraph requires explicit user authorization evidence.")
            else:
                codegraph_trial_authorized = True
            if re.search(r"auto\s*hook|auto\s*index|automatic\s*index|default|自动\s*hook|自动\s*建?索引|默认|watch", evidence_lower):
                errors.append("CodeGraph trial-index-codegraph must not be caused by default hooks, automatic indexing, or watch.")
            if not codegraph_pilot_effect_present(progress_text):
                errors.append("CodeGraph trial-index-codegraph requires Structural Index Pilot Effect metrics with source_confirmed=yes.")
        if structural_status == "query-existing" and re.search(r"\bcodegraph\b|provider\s*[:=]\s*both", evidence_lower):
            if not evidence_has_source_confirmed_yes(structural_evidence):
                errors.append("CodeGraph query-existing requires source_confirmed=yes before it can be used as workflow evidence.")

    for row in extract_table(progress_text, "## Structural Index Query Evidence"):
        provider = normalize_status(row.get("provider", ""))
        decision = normalize_status(row.get("decision", ""))
        source_confirmed = normalize_status(row.get("source_confirmed", ""))
        if provider_includes_codegraph(provider) and decision == "query-existing" and not source_confirmed_yes(source_confirmed):
            errors.append("CodeGraph query-existing row requires source_confirmed=yes; confirm against source/tests before using it as evidence.")
        if provider_includes_codegraph(provider) and decision == "trial-index-codegraph":
            notes = row.get("notes", "").lower()
            row_authorized = codegraph_trial_authorized or bool(re.search(r"explicit|user|approved|授权|用户", notes))
            if not row_authorized:
                errors.append("CodeGraph trial-index-codegraph row requires explicit user authorization evidence before trial output can be used as workflow evidence.")
            if re.search(r"auto\s*hook|auto\s*index|automatic\s*index|default|自动\s*hook|自动\s*建?索引|默认|watch", notes):
                errors.append("CodeGraph trial-index-codegraph notes indicate default auto hook/watch, which is forbidden.")
            if not source_confirmed_yes(source_confirmed):
                errors.append("CodeGraph trial-index-codegraph row requires source_confirmed=yes before trial output can be used as workflow evidence.")
            if not codegraph_pilot_effect_present(progress_text):
                errors.append("CodeGraph trial-index-codegraph row requires Structural Index Pilot Effect metrics with source_confirmed=yes.")

    result: dict[str, Any] = {
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "workflow_trace_rows": sorted(rows.keys()),
        "trace_artifact": trace_artifact or None,
        "trace_artifact_loaded": trace_data is not None,
    }
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate progress Workflow Trace consistency without running live agents or creating a second workflow state."
    )
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan path, relative to root unless absolute.")
    parser.add_argument("--progress", default="progress.md", help="Progress path, relative to root unless absolute.")
    parser.add_argument("--trace-artifact", default=None, help="Optional derived .agent-state/runs/<run_id>/workflow-trace.json artifact.")
    parser.add_argument("--strict-trigger", action="store_true", help="Require Workflow Trace for high/release style checks.")
    parser.add_argument("--check-template", action="store_true", help="Validate raw template files instead of skipping them.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    task_plan = Path(args.task_plan)
    progress = Path(args.progress)
    if not task_plan.is_absolute():
        task_plan = root / task_plan
    if not progress.is_absolute():
        progress = root / progress

    result = validate(
        root=root,
        task_plan_path=task_plan,
        progress_path=progress,
        trace_artifact=args.trace_artifact,
        check_template=args.check_template,
        strict_trigger=args.strict_trigger,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        for warning in result.get("warnings", []):
            print(f"warning: {warning}")
        for error in result.get("errors", []):
            print(f"error: {error}")

    return 0 if result["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
