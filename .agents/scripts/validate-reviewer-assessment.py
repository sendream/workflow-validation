#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc
import workflow_routing as wr


PLACEHOLDERS = {
    "",
    "待填写",
    "missing",
    "pending",
    "required",
    "yes / no",
    "not-needed / preferred / started / unavailable / incomplete",
    "none / policy-auto / task / session / revoked",
    "none / policy-auto / task / session / external-standing-opt-in / revoked",
    "yes / no / not-needed",
    "started / unavailable / incomplete / not-needed",
    "not-needed / policy-auto-started / task-authorized-started / session-authorized-started / external-opt-in-started / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / budget-exceeded / explicit-denied",
    "not-created",
}
TEMPLATE_MARKERS = ("待填写", "<run_id>")
HIGH_RISK_TIERS = wr.HIGH_RISK_TIERS
RESOLVED_DISPOSITIONS = {"accepted", "rejected", "needs-more-evidence", "deferred"}
ROLE_REVIEW_PLACEHOLDERS = {"", "not-needed", "待填写"}
VALID_DECISIONS = wr.REVIEWER_TRIGGER_DECISIONS
LEGACY_TRIGGER_DECISIONS = wr.REVIEWER_LEGACY_TRIGGER_DECISIONS
PREFERRED_DECISIONS = {"preferred"}
NO_START_DECISIONS = {"not-needed", "assessment-only"}
AUTHORIZED_SCOPES = wr.REVIEWER_AUTHORIZED_SCOPES
VALID_AUTH_SCOPES = wr.REVIEWER_AUTH_SCOPES
VALID_START_REQUIRED = {"yes", "no", "not-needed"}
VALID_START_RESULTS = wr.REVIEWER_START_RESULTS
STARTED_RESULTS = wr.REVIEWER_STARTED_RESULTS
UNAVAILABLE_RESULTS = wr.REVIEWER_UNAVAILABLE_RESULTS
INCOMPLETE_RESULTS = wr.REVIEWER_INCOMPLETE_RESULTS
DENIED_RESULTS = wr.REVIEWER_DENIED_RESULTS
INVALID_PACKET_RESULTS = wr.REVIEWER_INVALID_PACKET_RESULTS
LEGACY_STRICT_START_RESULTS = wr.REVIEWER_LEGACY_STRICT_START_RESULTS
PRE_START_NON_START_RESULTS = {
    "tool-unavailable",
    "runtime-policy-blocked",
    "explicit-delegation-required",
    "packet-invalid",
    "brief-invalid",
    "validator-failed",
    "explicit-denied",
}
POST_START_INCOMPLETE_RESULTS = {"review-incomplete", "reviewer-timeout", "budget-exceeded"}
AUTHORITY_MODES = wr.REVIEWER_AUTHORITY_MODES
PACKET_VALIDATOR_STATUSES = {"pass", "fail", "not-run", "not-needed"}
SUBMITTED_LIFECYCLE_STATES = {"submitted", "archived", "completed-and-submitted"}
SUBMITTED_PACKET_RETENTION = "not-retained-after-submission"
VALID_RUNTIME_BUDGET_TERMS = (
    "hard-timeout",
    "hard timeout",
    "hard-turn",
    "hard turn",
    "hard-turn-limit",
    "hard turn limit",
    "hard-file",
    "hard file",
    "hard-file-limit",
    "hard file limit",
    "prompt-soft-limit",
    "prompt soft limit",
    "manual-fallback",
    "manual fallback",
)
BUDGET_NEGATION_PATTERNS = (
    r"\b(?:no|not|without|missing|absent|lack|lacks|lacking|unavailable)\b.{0,48}\b(?:budget|timeout|turn|file|limit|manual fallback|hard timeout|hard turn|hard file|prompt soft)\b",
    r"\b(?:budget|timeout|turn|file|limit|manual fallback|hard timeout|hard turn|hard file|prompt soft)\b.{0,48}\b(?:not configured|missing|absent|unavailable|required but missing)\b",
    r"(?:无|没有|未设置|缺少).{0,24}(?:预算|超时|轮次|文件|限制)",
)
NO_AUTH_TERMS = (
    "no authorization",
    "not authorized",
    "not-authorized",
    "without authorization",
    "no user authorization",
    "user did not authorize",
    "未授权",
    "没有授权",
)
EXTERNAL_REVIEWER_TERMS = (
    "gemini",
    "claude",
    "external",
    "third-party",
    "第三方",
    "外部",
)
PREFERRED_SIGNALS = (
    "auth",
    "permission",
    "tenant",
    "db",
    "database",
    "migration",
    "data repair",
    "deploy",
    "deployment",
    "rollback",
    "container",
    "waiver",
    "tooling gap",
    "dirty worktree",
    "dirty-worktree",
    "long-session",
    "long session",
    "wsl",
    "ssh",
    "docker",
)
NARRATIVE_REVIEWER_TERMS = (
    "reviewer",
    "subagent",
    "sub-agent",
    "子 agent",
    "子agent",
    "子代理",
    "审查者",
    "复核",
)
NARRATIVE_REVIEW_PASS_TERMS = (
    " pass",
    "passed",
    "通过",
    "无阻断",
    "no blockers",
    "no blocking",
)
ADJUDICATIVE_AGENT_SECTIONS = (
    "## Role Review Summary",
    "## Isolated Reviewer",
    "## Isolated Reviewer Assessment",
    "## Reviewer Assessment",
    "## Final Evidence Ledger",
)
ADJUDICATIVE_AGENT_ALIAS_RE = re.compile(
    r"(?:\b(?:explorer|search[ -](?:agent|worker)|verification[ -](?:agent|worker)|mechanical[ -]agent|implementation[ -]worker)\b|"
    r"探索(?:代理|agent)|搜索(?:代理|agent)|验证(?:代理|agent)|机械(?:代理|agent)|实现(?:代理|worker))",
    re.IGNORECASE,
)
ADJUDICATIVE_VERDICT_RE = re.compile(
    r"(?:\b(?:pass(?:ed)?|approv(?:e|ed)|accept(?:ed)?|block(?:ed|ing)?|ship(?:ped)?|waiv(?:e|ed|er)|"
    r"no[ -]blockers?|no[ -]blocking)\b|通过|批准|接受|验收|阻断|无阻断|交付|豁免)",
    re.IGNORECASE,
)


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_budget(value: str) -> str:
    return clean_cell(value).lower().replace("_", " ")


def has_runtime_budget(value: str) -> bool:
    normalized = normalize_budget(value)
    if is_placeholder(normalized, allow_not_needed=True) or normalized == "not-needed":
        return False
    if has_budget_negation(normalized):
        return False
    return any(term in normalized or term.replace("-", " ") in normalized for term in VALID_RUNTIME_BUDGET_TERMS)


def has_budget_negation(value: str) -> bool:
    normalized = normalize_budget(value)
    return any(re.search(pattern, normalized) for pattern in BUDGET_NEGATION_PATTERNS)


def has_multi_reviewer_budget_signal(value: str) -> bool:
    normalized = normalize_budget(value)
    if has_budget_negation(normalized):
        return False
    return bool(
        re.search(
            r"(?:\b(?:budget|time budget|token budget|max time|max elapsed|minutes?|mins?|tokens?|scope-limited)\b|\d+\s*(?:m|min|mins|minutes|分钟|tokens?|k)|预算|限额|最大时长|分钟|令牌)",
            normalized,
        )
    )


def has_concrete_input_package(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if is_placeholder(normalized, allow_not_needed=True):
        return False
    return normalized not in {"not-needed", "not-created"}


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def is_placeholder(value: str, allow_not_needed: bool = False) -> bool:
    normalized = clean_cell(value).lower()
    if allow_not_needed and normalized == "not-needed":
        return False
    if normalized in PLACEHOLDERS:
        return True
    return any(marker.lower() in normalized for marker in TEMPLATE_MARKERS)


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


def extract_named_section_value(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading)).lower()


def extract_risk_tier(markdown_text: str) -> str | None:
    return wr.extract_risk_tier(markdown_text)


def reviewer_assessment(rows: list[dict[str, str]]) -> dict[str, str]:
    assessment: dict[str, str] = {}
    for row in rows:
        item = normalize_key(row.get("item", ""))
        value = row.get("value", "")
        if item:
            assessment[item] = value
    return assessment


def duplicate_reviewer_assessment_items(rows: list[dict[str, str]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        item = normalize_key(row.get("item", ""))
        if not item:
            continue
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return sorted(duplicates)


def key_value_table(markdown_text: str, heading: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in extract_table(markdown_text, heading):
        item = normalize_key(row.get("item", ""))
        value = row.get("value", "")
        if item:
            values[item] = value
    return values


def progress_lifecycle_state(progress_text: str) -> str:
    current = key_value_table(progress_text, "## Current Status")
    value = clean_cell(current.get("lifecycle_state", "")).lower().replace("_", "-").replace(" ", "-")
    if value:
        return value
    match = re.search(r"(?im)^\s*-\s*Lifecycle state:\s*([^\n]+)$", progress_text)
    if not match:
        return ""
    return clean_cell(match.group(1)).lower().replace("_", "-").replace(" ", "-")


def durable_review_summary_error(progress_path: Path, value: str) -> str | None:
    path_text = clean_cell(value)
    if is_placeholder(path_text, allow_not_needed=True) or path_text == "not-needed":
        return "submitted reviewer packet compaction requires Durable review summary"
    path = Path(path_text)
    if path.is_absolute():
        return "Durable review summary must be a repository-relative docs/ or .agents/tasks/ path"
    root = progress_path.parent.resolve()
    candidate = (root / path).resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return "Durable review summary must stay inside the repository"
    if not (relative.parts[:1] == ("docs",) or relative.parts[:2] == (".agents", "tasks")):
        return "Durable review summary must live under docs/ or .agents/tasks/"
    if not candidate.is_file():
        return f"Durable review summary does not exist: {path_text}"
    return None


def durable_review_summary_is_tracked(progress_path: Path, value: str) -> bool:
    root = progress_path.parent.resolve()
    candidate = (root / clean_cell(value)).resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative.as_posix()],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def parse_intish(value: str) -> int | None:
    normalized = clean_cell(value).lower()
    match = re.search(r"\d+", normalized)
    if not match:
        return None
    return int(match.group(0))


def start_result_is_started(value: str) -> bool:
    return clean_cell(value).lower() in STARTED_RESULTS


def start_result_is_unavailable(value: str) -> bool:
    return clean_cell(value).lower() in UNAVAILABLE_RESULTS


def start_result_is_incomplete(value: str) -> bool:
    return clean_cell(value).lower() in INCOMPLETE_RESULTS


def start_result_is_invalid_packet(value: str) -> bool:
    return clean_cell(value).lower() in INVALID_PACKET_RESULTS


def start_result_is_runtime_policy_blocked(value: str) -> bool:
    return clean_cell(value).lower() in {"runtime-policy-blocked", "explicit-delegation-required"}


def start_result_is_denied(value: str) -> bool:
    return clean_cell(value).lower() in DENIED_RESULTS


def start_result_is_pre_start_non_start(value: str) -> bool:
    return clean_cell(value).lower() in PRE_START_NON_START_RESULTS


def start_result_requires_start_required_yes(value: str) -> bool:
    normalized = clean_cell(value).lower()
    return normalized in STARTED_RESULTS or normalized in POST_START_INCOMPLETE_RESULTS


def concrete_packet_path(value: str) -> bool:
    normalized = clean_cell(value).lower()
    return bool(normalized) and normalized not in {"not-created", "not-needed"} and not is_placeholder(normalized)


def risk_context(task_plan_text: str, progress_text: str) -> dict[str, Any]:
    routing = wr.parse_task_routing(task_plan_text)
    risk_section = "\n".join(
        part
        for part in (
            extract_named_section_value(task_plan_text, "## Workflow Routing"),
            extract_named_section_value(task_plan_text, "## Risk Tier"),
        )
        if part
    )
    impact_section = "\n".join(
        part
        for part in (
            extract_named_section_value(task_plan_text, "## Workflow Routing"),
            extract_named_section_value(task_plan_text, "## Impact Scope"),
            extract_named_section_value(task_plan_text, "## Risk Tier"),
        )
        if part
    )
    structured_review_text = "\n".join(
        [
            risk_section,
            impact_section,
            extract_named_section_value(task_plan_text, "## Isolated Reviewer Assessment"),
            extract_named_section_value(progress_text, "## Isolated Reviewer"),
            extract_named_section_value(progress_text, "## Reviewer Start Authority"),
            extract_named_section_value(progress_text, "## Release Artifact Source Gate"),
            extract_named_section_value(progress_text, "## Verification Waivers"),
        ]
    ).lower()

    tier = routing.risk_tier.value if routing.risk_tier is not None else None
    high_or_release = tier in HIGH_RISK_TIERS if tier is not None else False
    release = tier == "release" if tier is not None else False
    external_system = routing.impact_scope.value == "external-system" if routing.impact_scope is not None else False
    preferred_signals = [signal for signal in PREFERRED_SIGNALS if signal in structured_review_text]
    preferred_required = release and external_system and bool(preferred_signals)

    return {
        "tier": tier,
        "risk_section": risk_section.strip(),
        "impact_section": impact_section.strip(),
        "high_or_release": high_or_release,
        "release": release,
        "external_system": external_system,
        "preferred_signals": preferred_signals,
        "preferred_required": preferred_required,
    }


def role_review_summary_has_disposition(progress_text: str) -> bool:
    rows = extract_table(progress_text, "## Role Review Summary")
    for row in rows:
        disposition = clean_cell(row.get("disposition", "")).lower()
        if disposition in RESOLVED_DISPOSITIONS:
            return True
    return False


def role_review_summary_rows(progress_text: str) -> list[dict[str, str]]:
    real_rows: list[dict[str, str]] = []
    for row in extract_table(progress_text, "## Role Review Summary"):
        role = clean_cell(row.get("role", "")).lower()
        if role in ROLE_REVIEW_PLACEHOLDERS:
            continue
        real_rows.append(row)
    return real_rows


def role_review_summary_disposition_errors(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        role = clean_cell(row.get("role", "unknown"))
        disposition = clean_cell(row.get("disposition", "")).lower()
        if disposition not in RESOLVED_DISPOSITIONS:
            errors.append(f"Role Review Summary row for {role} requires main Codex disposition")
    return errors


def explicit_extra_reviewer_budget(progress_text: str) -> bool:
    text = progress_text.lower()
    return ("explicit user" in text or "用户明确" in text or "user request" in text) and (
        "budget" in text or "预算" in text or "time" in text or "token" in text
    )


def explicit_multi_reviewer_context(progress_text: str) -> bool:
    authority = key_value_table(progress_text, "## Reviewer Start Authority")
    assessment = reviewer_assessment(extract_table(progress_text, "## Isolated Reviewer"))
    role_rows = role_review_summary_rows(progress_text)
    values: list[str] = []
    for key in ("authority_source", "budget_note", "authorized_roles", "expires"):
        values.append(authority.get(key, ""))
    for key in ("reason", "authorization_source", "fallback"):
        values.append(assessment.get(key, ""))
    for row in role_rows:
        values.extend(row.values())
    text = "\n".join(values).lower()
    explicit_experiment_or_audit = any(
        term in text
        for term in ("explicit experiment", "broad audit", "broad-audit", "campaign metrics", "显式实验", "宽范围审计", "多视角审计")
    )
    explicit_user = any(term in text for term in ("explicit user", "user request", "用户明确"))
    scoped_budget = has_multi_reviewer_budget_signal(text)
    return (explicit_experiment_or_audit or explicit_user) and scoped_budget


def narrative_reviewer_pass_claims(progress_text: str) -> list[str]:
    claims: list[str] = []
    for raw_line in progress_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("|") or set(line) <= {"-", ":", " "}:
            continue
        normalized = line.lower()
        has_reviewer = any(term in normalized for term in NARRATIVE_REVIEWER_TERMS)
        has_pass = any(term in normalized for term in NARRATIVE_REVIEW_PASS_TERMS)
        if has_reviewer and has_pass:
            claims.append(line)
    return claims


def adjudicative_agent_alias_claims(progress_text: str) -> list[tuple[str, str]]:
    claims: list[tuple[str, str]] = []
    for heading in ADJUDICATIVE_AGENT_SECTIONS:
        section = md_doc.section(progress_text, heading)
        if section is None:
            continue
        visible_lines = md_doc.without_fenced_blocks(section.text).splitlines()
        for raw_line in visible_lines:
            line = raw_line.strip()
            if not line or set(line) <= {"|", "-", ":", " "}:
                continue
            if ADJUDICATIVE_AGENT_ALIAS_RE.search(line) and ADJUDICATIVE_VERDICT_RE.search(line):
                claims.append((heading, line))
    return claims


def validate(
    task_plan_path: Path,
    progress_path: Path,
    strict_trigger: bool = False,
    check_template: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not task_plan_path.is_file():
        return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": []}
    if not progress_path.is_file():
        return {"status": "fail", "errors": [f"progress file not found: {progress_path}"], "warnings": []}

    if (is_template_path(task_plan_path) or is_template_path(progress_path)) and not check_template:
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "strict_trigger_required": False,
            "assessment_present": False,
            "trigger_decision": "",
            "preferred_required": False,
        }

    task_text = task_plan_path.read_text(encoding="utf-8")
    progress_text = progress_path.read_text(encoding="utf-8")
    context = risk_context(task_text, progress_text)
    alias_claims = adjudicative_agent_alias_claims(progress_text)
    strict_required = strict_trigger and (wr.reviewer_route_requested(progress_text) or bool(alias_claims))
    narrative_claims = narrative_reviewer_pass_claims(progress_text)

    rows = extract_table(progress_text, "## Isolated Reviewer")
    duplicate_assessment_items = duplicate_reviewer_assessment_items(rows)
    errors.extend(
        f"Isolated Reviewer table contains duplicate item: {item}"
        for item in duplicate_assessment_items
    )
    assessment = reviewer_assessment(rows)
    assessment_present = bool(assessment)
    trigger_decision = clean_cell(assessment.get("trigger_decision", "")).lower()
    required_assessment = clean_cell(assessment.get("required_assessment", "")).lower()
    reason = assessment.get("reason", "")
    fallback = assessment.get("fallback", "")
    authorization_scope = clean_cell(assessment.get("authorization_scope", "")).lower()
    authorization_source = assessment.get("authorization_source", "")
    start_required = clean_cell(assessment.get("start_required", "")).lower()
    start_result = clean_cell(assessment.get("start_result", "")).lower()
    input_package = assessment.get("input_package", "")
    reviewer_tool = assessment.get("reviewer_tool", "")
    review_mode = clean_cell(assessment.get("review_mode", "")).lower()
    packet_validator_status = clean_cell(assessment.get("packet_validator_status", "")).lower()
    packet_validator_command = assessment.get("packet_validator_command", "")
    packet_validator_exit_code = clean_cell(assessment.get("packet_validator_exit_code", "")).lower()
    packet_validator_artifact = assessment.get("packet_validator_artifact", "")
    packet_retention = clean_cell(assessment.get("packet_retention", "")).lower()
    durable_review_summary = assessment.get("durable_review_summary", "")
    reviewer_verdict = clean_cell(assessment.get("verdict", "")).lower()
    reviewer_disposition = clean_cell(assessment.get("disposition", "")).lower()
    reviewer_fallback = clean_cell(assessment.get("fallback", "")).lower()
    runtime_policy_status = clean_cell(assessment.get("runtime_policy_status", "")).lower()
    runtime_enforced_budget = assessment.get("runtime_enforced_budget", "")
    authority = key_value_table(progress_text, "## Reviewer Start Authority")
    authority_mode = clean_cell(authority.get("authority_mode", "")).lower()
    authority_source = authority.get("authority_source", authority.get("source", ""))
    authority_scope = clean_cell(authority.get("scope", "")).lower()
    authority_run_id = clean_cell(authority.get("run_id", ""))
    authority_repo_path = clean_cell(authority.get("repo_path", ""))
    authority_max_reviewers = clean_cell(authority.get("max_reviewers", ""))
    authority_external_allowed = clean_cell(authority.get("external_model_allowed", "")).lower()
    authority_expires = clean_cell(authority.get("expires", "")).lower()
    input_package_normalized = clean_cell(input_package).lower()
    reason_and_tool = f"{reason}\n{reviewer_tool}".lower()
    authorized = authorization_scope in AUTHORIZED_SCOPES
    policy_auto = authorization_scope == "policy-auto"
    external_standing = authorization_scope == "external-standing-opt-in"
    external_reviewer = any(term in clean_cell(reviewer_tool).lower() for term in EXTERNAL_REVIEWER_TERMS)
    has_role_review_disposition = role_review_summary_has_disposition(progress_text)
    role_rows = role_review_summary_rows(progress_text)
    role_count = len(role_rows)
    started_result = start_result_is_started(start_result)
    invalid_packet_result = start_result_is_invalid_packet(start_result)
    runtime_policy_blocked_result = start_result_is_runtime_policy_blocked(start_result)
    explicit_denied_result = start_result == "explicit-denied"
    start_attempted = started_result or start_result_is_unavailable(start_result) or start_result_is_incomplete(start_result) or invalid_packet_result
    reviewer_path_recorded = start_attempted or explicit_denied_result
    lifecycle_state = progress_lifecycle_state(progress_text)
    submitted_packet_compaction = (
        lifecycle_state in SUBMITTED_LIFECYCLE_STATES
        and packet_retention == SUBMITTED_PACKET_RETENTION
        and started_result
    )
    packet_explicitly_not_needed = all(
        clean_cell(value).lower() == "not-needed"
        for value in (
            packet_validator_status,
            packet_validator_command,
            packet_validator_exit_code,
            packet_validator_artifact,
            packet_retention,
        )
    )
    local_durable_completion_candidate = (
        trigger_decision == "assessment-only"
        and authorization_scope == "task"
        and start_result == "task-authorized-started"
        and reviewer_verdict == "pass"
        and clean_cell(reviewer_tool).lower() == "fresh isolated codex subagent"
        and review_mode == "direct-local-isolated"
        and runtime_policy_status == "allowed-local-only"
        and authority_external_allowed == "no"
        and authority_scope == "read-only reviewer"
        and parse_intish(authority_max_reviewers) == 1
        and reviewer_fallback == "not-needed"
        and packet_explicitly_not_needed
    )
    local_durable_completion = False

    if start_result_is_incomplete(start_result) and reviewer_verdict == "pass":
        errors.append("incomplete reviewer Start result cannot coexist with Verdict = pass")

    if local_durable_completion_candidate:
        local_completion_errors: list[str] = []
        if reviewer_disposition not in RESOLVED_DISPOSITIONS:
            local_completion_errors.append("completed local durable assessment requires a resolved Disposition")
        if not has_concrete_input_package(input_package):
            local_completion_errors.append("completed local durable assessment requires a concrete Input package")
        durable_error = durable_review_summary_error(progress_path, durable_review_summary)
        if durable_error:
            local_completion_errors.append(durable_error)
        elif not durable_review_summary_is_tracked(progress_path, durable_review_summary):
            local_completion_errors.append("completed local durable assessment requires a tracked Durable review summary")
        matching_role_rows = [
            row
            for row in role_rows
            if clean_cell(row.get("packet", "")) == clean_cell(durable_review_summary)
            and clean_cell(row.get("verdict", "")).lower() == "pass"
            and clean_cell(row.get("disposition", "")).lower() in RESOLVED_DISPOSITIONS
            and clean_cell(row.get("unresolved_risk", "")).lower() == "none"
        ]
        if len(matching_role_rows) != 1:
            local_completion_errors.append(
                "completed local durable assessment requires one matching PASS Role Review Summary row with no unresolved risk"
            )
        errors.extend(local_completion_errors)
        local_durable_completion = not local_completion_errors

    if packet_retention == SUBMITTED_PACKET_RETENTION:
        if lifecycle_state not in SUBMITTED_LIFECYCLE_STATES:
            errors.append("reviewer packet compaction is only valid after submitted/archived lifecycle")
        if not started_result:
            errors.append("submitted reviewer packet compaction requires a successfully started reviewer")
        if reviewer_verdict != "pass":
            errors.append("submitted reviewer packet compaction requires Verdict = pass")
        if reviewer_disposition not in RESOLVED_DISPOSITIONS:
            errors.append("submitted reviewer packet compaction requires resolved main Codex Disposition")
        durable_error = durable_review_summary_error(progress_path, durable_review_summary)
        if durable_error:
            errors.append(durable_error)

    if assessment_present and trigger_decision in LEGACY_TRIGGER_DECISIONS:
        message = "Isolated Reviewer Trigger decision must be not-needed/assessment-only/preferred; start and non-start outcomes belong in Start result"
        if strict_trigger or context["high_or_release"] or context["external_system"]:
            errors.append(message)
        else:
            warnings.append(message)
    if assessment_present and policy_auto and not (context["high_or_release"] or context["external_system"]):
        errors.append("policy-auto reviewer authorization is only valid for high/release/external-system tasks")
    if assessment_present and external_reviewer and policy_auto:
        errors.append("external model reviewer cannot use policy-auto; use external-standing-opt-in/task/session with standing opt-in")

    if strict_required and not assessment_present:
        errors.append("reviewer-routed tasks require an Isolated Reviewer assessment record in progress.md")
        if alias_claims:
            errors.append(
                "adjudicative agent alias claim requires structured Isolated Reviewer assessment; agent name or tool label cannot bypass G16"
            )
        if narrative_claims:
            errors.append(
                "natural-language reviewer/subagent claims do not satisfy Isolated Reviewer assessment; record Reviewer Start Authority, structured Isolated Reviewer rows, Role Review Summary, and packet/result artifact links"
            )
    for heading, _line in alias_claims:
        if heading != "## Role Review Summary":
            errors.append(
                f"adjudicative agent alias claim cannot be used directly in {heading.removeprefix('## ')}; record the governed result in Role Review Summary"
            )
    if strict_required and assessment_present:
        if required_assessment != "yes":
            errors.append("reviewer-routed tasks require Isolated Reviewer Required assessment = yes")
        if is_placeholder(authorization_scope, allow_not_needed=True):
            errors.append("reviewer-routed tasks require Isolated Reviewer Authorization scope")
        elif authorization_scope not in VALID_AUTH_SCOPES:
            errors.append(f"Isolated Reviewer Authorization scope is invalid: {authorization_scope}")
        if authorization_scope in {"task", "session"} and is_placeholder(authorization_source):
            errors.append("task/session reviewer authorization requires Authorization source")
        if external_standing and is_placeholder(authorization_source):
            errors.append("external-standing-opt-in reviewer authorization requires Authorization source")
        if policy_auto:
            if not context["high_or_release"] and not context["external_system"]:
                errors.append("policy-auto reviewer authorization is only valid for high/release/external-system tasks")
            if "agents.md" not in authorization_source.lower() and "policy-auto" not in authorization_source.lower():
                errors.append("policy-auto reviewer authorization requires Authorization source = AGENTS.md Policy-Auto Reviewer")
            if external_reviewer:
                errors.append("external model reviewer cannot use policy-auto; use external-standing-opt-in/task/session with standing opt-in")
        if external_reviewer and not policy_auto:
            if authorization_scope not in {"external-standing-opt-in", "task", "session"}:
                errors.append("external model reviewer requires external-standing-opt-in, task, or session authorization")
            if "standing opt-in" not in progress_text.lower() and "external model allowed | yes-with-standing-opt-in" not in progress_text.lower():
                errors.append("external model reviewer requires standing opt-in and redacted packet scope")
        if is_placeholder(start_required, allow_not_needed=True):
            errors.append("reviewer-routed tasks require Isolated Reviewer Start required")
        elif start_required not in VALID_START_REQUIRED:
            errors.append(f"Isolated Reviewer Start required is invalid: {start_required}")
        if is_placeholder(start_result, allow_not_needed=True):
            errors.append("reviewer-routed tasks require Isolated Reviewer Start result")
        elif start_result not in VALID_START_RESULTS:
            errors.append(f"Isolated Reviewer Start result is invalid: {start_result}")
        elif start_result in LEGACY_STRICT_START_RESULTS:
            errors.append("strict reviewer assessment requires typed Start result; legacy started/unavailable/incomplete/not-authorized is compatibility-only")
        if runtime_policy_blocked_result:
            if runtime_policy_status not in {"runtime-policy-blocked", "explicit-delegation-required"}:
                errors.append("runtime policy blocked reviewer path requires Runtime policy status = runtime-policy-blocked or explicit-delegation-required")
            if is_placeholder(fallback):
                errors.append("runtime policy blocked reviewer path requires local fallback evidence")
        needs_runtime_budget = authorized and (
            started_result
            or start_result_is_unavailable(start_result)
            or start_result_is_incomplete(start_result)
            or trigger_decision == "preferred"
        )
        if needs_runtime_budget and not has_runtime_budget(runtime_enforced_budget):
            errors.append("authorized reviewer start/non-start paths require Runtime-enforced budget with hard timeout/turn/file limit, prompt-soft-limit, or manual-fallback")
        if is_placeholder(trigger_decision):
            errors.append("Isolated Reviewer Trigger decision is missing")
        elif trigger_decision in LEGACY_TRIGGER_DECISIONS:
            errors.append("Isolated Reviewer Trigger decision must not contain runtime start/non-start outcomes")
        elif trigger_decision not in VALID_DECISIONS:
            errors.append(f"Isolated Reviewer Trigger decision is invalid: {trigger_decision}")
        if trigger_decision in NO_START_DECISIONS and is_placeholder(reason):
            errors.append("Isolated Reviewer assessment-only/not-needed requires a concrete Reason")
        if (start_result_is_unavailable(start_result) or start_result_is_incomplete(start_result) or invalid_packet_result or explicit_denied_result) and is_placeholder(fallback):
            errors.append("Isolated Reviewer non-start/invalid-packet paths require a concrete Fallback")
        if explicit_denied_result:
            if start_required != "no":
                errors.append("explicit-denied reviewer paths require Start required = no")
            if authorization_scope != "revoked":
                errors.append("explicit-denied reviewer path requires Authorization scope = revoked")
            denied_evidence = f"{reason}\n{authorization_source}".lower()
            if not any(term in denied_evidence for term in ("declined", "denied", "refused", "revoked", "do not start", "不要启动", "拒绝", "撤销")):
                errors.append("explicit-denied reviewer path requires direct user denial/revocation evidence in Reason or Authorization source")

        if authorized and (start_attempted or trigger_decision == "preferred"):
            if not authority:
                errors.append("Reviewer Start Authority table is required for authorized reviewer start/unavailable/incomplete paths")
            else:
                if authority_mode not in AUTHORITY_MODES:
                    errors.append(f"Reviewer Start Authority mode is invalid: {authority_mode}")
                if policy_auto and authority_mode != "policy-auto":
                    errors.append("policy-auto reviewer requires Reviewer Start Authority mode = policy-auto")
                if authorization_scope == "task" and authority_mode != "task-authorized":
                    errors.append("task-authorized reviewer requires Reviewer Start Authority mode = task-authorized")
                if authorization_scope == "session" and authority_mode != "session-authorized":
                    errors.append("session-authorized reviewer requires Reviewer Start Authority mode = session-authorized")
                if external_standing and authority_mode != "external-standing-opt-in":
                    errors.append("external-standing-opt-in reviewer requires Reviewer Start Authority mode = external-standing-opt-in")
                if authority_scope != "read-only reviewer":
                    errors.append("Reviewer Start Authority scope must be read-only reviewer for role reviewers")
                if is_placeholder(authority_run_id, allow_not_needed=True):
                    errors.append("Reviewer Start Authority requires Run ID for reviewer start paths")
                if is_placeholder(authority_repo_path, allow_not_needed=True):
                    errors.append("Reviewer Start Authority requires Repo path for reviewer start paths")
                if is_placeholder(authority_expires, allow_not_needed=True):
                    errors.append("Reviewer Start Authority requires Expires for reviewer start paths")
                if policy_auto and is_placeholder(authority_source):
                    errors.append("policy-auto reviewer requires Reviewer Start Authority Authority source = AGENTS.md Policy-Auto Reviewer")
                if external_reviewer and authority_external_allowed != "yes-with-standing-opt-in":
                    errors.append("external model reviewer requires External model allowed = yes-with-standing-opt-in")
                max_reviewers = parse_intish(authority_max_reviewers)
                if role_count and max_reviewers is not None and role_count > max_reviewers:
                    errors.append("Role Review Summary reviewer count exceeds Reviewer Start Authority Max reviewers")

        if (started_result or invalid_packet_result) and not submitted_packet_compaction and not local_durable_completion:
            if is_placeholder(packet_validator_status, allow_not_needed=True):
                errors.append("reviewer start/packet-invalid paths require Packet validator status")
            elif packet_validator_status not in PACKET_VALIDATOR_STATUSES:
                errors.append(f"Packet validator status is invalid: {packet_validator_status}")
            if is_placeholder(packet_validator_command, allow_not_needed=True):
                errors.append("reviewer start/packet-invalid paths require Packet validator command")
            elif "validate-role-review-packet.py" not in packet_validator_command:
                errors.append("Packet validator command must run validate-role-review-packet.py")
            if is_placeholder(packet_validator_exit_code, allow_not_needed=True):
                errors.append("reviewer start/packet-invalid paths require Packet validator exit code")
            if is_placeholder(packet_validator_artifact, allow_not_needed=True):
                errors.append("reviewer start/packet-invalid paths require Packet validator artifact")
            elif not clean_cell(packet_validator_artifact).startswith(".agent-state/runs/"):
                errors.append("Packet validator artifact must live under .agent-state/runs/<run_id>/")
            if started_result:
                if packet_validator_status and packet_validator_status != "pass":
                    errors.append("started reviewer requires Packet validator status = pass")
                if packet_validator_exit_code and packet_validator_exit_code != "0":
                    errors.append("started reviewer requires Packet validator exit code = 0")
            if invalid_packet_result:
                if packet_validator_status and packet_validator_status != "fail":
                    errors.append("packet-invalid/brief-invalid reviewer requires Packet validator status = fail")
            if is_placeholder(input_package):
                errors.append("reviewer start/packet-invalid paths require concrete Input package")
            elif not input_package_normalized.startswith(".agent-state/runs/"):
                errors.append("reviewer packet must live under .agent-state/runs/<run_id>/")
        elif submitted_packet_compaction:
            if packet_validator_status != "pass":
                errors.append("submitted reviewer packet compaction requires Packet validator status = pass")
            if packet_validator_exit_code != "0":
                errors.append("submitted reviewer packet compaction requires Packet validator exit code = 0")

    if strict_trigger and context["preferred_required"]:
        if not assessment_present:
            errors.append("release/external-system preferred reviewer trigger requires assessment record")
        elif trigger_decision in NO_START_DECISIONS:
            signals = ", ".join(context["preferred_signals"])
            errors.append(f"release + external-system preferred reviewer signals require Trigger decision=preferred plus typed Start result, got {trigger_decision}: {signals}")
        elif authorization_scope in {"none", "not-needed", "revoked"} and not explicit_denied_result:
            errors.append("release + external-system preferred internal reviewer signals require policy-auto/task/session/external-standing-opt-in start authority; missing user authorization cannot skip reviewer assessment")
        elif authorized and any(term in reason_and_tool for term in NO_AUTH_TERMS):
            errors.append("preferred reviewer has policy-auto/task/session/external-standing-opt-in authorization; non-start cannot be justified by missing user authorization")
        elif trigger_decision in PREFERRED_DECISIONS and (
            start_result_is_unavailable(start_result) or start_result_is_incomplete(start_result) or invalid_packet_result or explicit_denied_result
        ) and is_placeholder(fallback):
            errors.append("preferred reviewer unavailable/incomplete path requires fallback evidence")
        if assessment_present and authorized:
            if start_result_requires_start_required_yes(start_result) and start_required != "yes":
                errors.append("started/review-incomplete reviewer paths require Start required = yes")
            if start_result_is_pre_start_non_start(start_result) and start_required != "no":
                errors.append("pre-start non-start reviewer paths require Start required = no")
            if trigger_decision == "preferred" and not start_attempted:
                errors.append("authorized preferred reviewer cannot remain only preferred; it must start or record a typed non-start result")
            if (started_result or invalid_packet_result) and is_placeholder(input_package):
                errors.append("authorized reviewer start/invalid-packet path requires concrete Input package")
            if policy_auto and not submitted_packet_compaction and input_package_normalized not in {"not-created", "not-needed", ""} and not input_package_normalized.startswith(".agent-state/runs/"):
                errors.append("policy-auto reviewer packet must live under .agent-state/runs/<run_id>/")
        if assessment_present and not authorized and trigger_decision == "not-authorized":
            if not any(term in reason_and_tool for term in NO_AUTH_TERMS):
                errors.append("not-authorized reviewer decision requires explicit authorization reason")

    if strict_trigger and assessment_present:
        errors.extend(role_review_summary_disposition_errors(role_rows))
        if role_count > 1 and not (context["release"] and context["external_system"]) and not explicit_multi_reviewer_context(progress_text):
            errors.append("multiple role reviewers are only allowed for release + external-system, explicit experiment/broad audit, or explicit user-scoped budget")
        if role_count > 2 and not explicit_extra_reviewer_budget(progress_text):
            errors.append("more than two role reviewers requires explicit user request plus scope/time/token budget")
        if context["tier"] == "low" and trigger_decision in {"preferred", "started"} and not authorized:
            errors.append("low/fast-path tasks cannot start or prefer isolated reviewer without explicit user authorization")
        if authorized and trigger_decision == "preferred" and not start_attempted:
            errors.append("authorized preferred reviewer cannot remain preferred; it must start or record a typed non-start result")
        if reviewer_path_recorded or has_concrete_input_package(input_package):
            if not has_role_review_disposition:
                errors.append("started/non-start reviewer paths require Role Review Summary with main Codex disposition")

    if assessment_present and not strict_required and trigger_decision and trigger_decision not in VALID_DECISIONS and trigger_decision not in LEGACY_TRIGGER_DECISIONS and not is_placeholder(trigger_decision):
        warnings.append(f"Isolated Reviewer Trigger decision is not recognized: {trigger_decision}")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "strict_trigger_required": strict_required,
        "assessment_present": assessment_present,
        "required_assessment": required_assessment,
        "trigger_decision": trigger_decision,
        "authorization_scope": authorization_scope,
        "start_required": start_required,
        "start_result": start_result,
        "preferred_required": context["preferred_required"],
        "preferred_signals": context["preferred_signals"],
        "high_or_release": context["high_or_release"],
        "release": context["release"],
        "external_system": context["external_system"],
        "role_review_disposition_present": has_role_review_disposition,
        "role_review_count": role_count,
        "lifecycle_state": lifecycle_state,
        "submitted_packet_compaction": submitted_packet_compaction,
        "adjudicative_agent_alias_claims": [
            {"section": heading.removeprefix("## "), "claim": line}
            for heading, line in alias_claims
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate that high/release tasks recorded isolated reviewer assessment.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan markdown file.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--strict-trigger", action="store_true", help="Require assessment for high/release and preferred reviewer signals.")
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
    task_plan_path = Path(args.task_plan)
    if not task_plan_path.is_absolute():
        task_plan_path = root / task_plan_path
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path

    payload = validate(
        task_plan_path,
        progress_path,
        strict_trigger=args.strict_trigger,
        check_template=args.check_template,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["status"])
        for error in payload.get("errors", []):
            print(f"error: {error}", file=sys.stderr)
        for warning in payload.get("warnings", []):
            print(f"warning: {warning}", file=sys.stderr)
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
