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
from review_result_contract import validate_falsification_attempts


REQUIRED_FILES = (
    "review-packet.md",
    "diff.patch",
    "changed-files.txt",
    "evidence-ledger.md",
    "waivers.md",
    "dirty-worktree-summary.json",
)

EVIDENCE_LEVELS = {"direct", "indirect", "unverified"}
SEVERITIES = {"S0", "S1", "S2", "S3"}
VERDICTS = {"pass", "needs-more-evidence", "blocking", "review-incomplete", "review-unverified"}
DISPOSITIONS = {"accepted", "rejected", "needs-more-evidence", "deferred"}
REVIEW_EVIDENCE_FIELDS = (
    "check_id",
    "command",
    "exit_code",
    "status",
    "artifact_path",
    "stdout_stderr_summary_path",
    "run_id",
    "timestamp",
    "waiver_id",
)
SCENARIO_METADATA_FIELDS = (
    "generated_at",
    "source_file",
    "source_section",
    "source_commit_or_worktree_state",
    "source_sha256",
    "generated_by",
    "readonly_snapshot",
    "authoritative_source",
)
REVIEWER_POLICY_FIELDS = (
    "allowed_actions",
    "prohibited_actions",
    "state_source_policy",
    "subdelegation",
)
REVIEWER_REPO_WRITE_FIELDS = ("repo_write_scope", "write_scope")
EXECUTION_METADATA_FIELDS = ("runtime_enforced_budget",)
AGENT_BRIEF_FIELDS = (
    "role",
    "task_class",
    "goal",
    "context",
    "ownership",
    "output_format",
    "stop_condition",
)
OUTPUT_CONTRACT_FIELDS = (
    "finding_id",
    "severity",
    "evidence_level",
    "linked_acceptance_id",
    "linked_scenario_id",
    "linked_slice_id",
    "case_class",
    "claim",
    "evidence",
    "recommended_disposition",
)
VALID_AGENT_ROLES = {
    "requirements",
    "plan-consistency",
    "architecture",
    "qa",
    "security",
    "release",
    "knowledge",
    "docs-api",
    "mixed",
}
VALID_TASK_CLASSES = {"exploration", "review", "verification", "handoff", "scoped-implementation"}
READ_ONLY_OWNERSHIPS = {"finding-only", "no-state-ownership"}
OUTPUT_FORMAT_TERMS = (
    "severity",
    "evidence_level",
    "linked_acceptance_id",
    "linked_scenario_id",
    "linked_slice_id",
    "case_class",
    "evidence",
    "recommended_disposition",
)
STOP_CONDITION_TERMS = (
    "max files",
    "max file",
    "max time",
    "max findings",
    "packet insufficient",
    "secret suspicion",
    "secret suspected",
    "secrets are suspected",
)
VALID_RUNTIME_BUDGET_TERMS = (
    "hard-timeout",
    "hard timeout",
    "hard turn",
    "hard-turn",
    "hard turn limit",
    "hard file",
    "hard-file",
    "hard file limit",
    "prompt-soft-limit",
    "prompt soft limit",
    "prompt soft",
    "manual-fallback",
    "manual fallback",
    "not-needed",
)
BUDGET_NEGATION_PATTERNS = (
    r"\b(?:no|not|without|missing|absent|lack|lacks|lacking|unavailable)\b.{0,48}\b(?:budget|timeout|turn|file|limit|manual fallback|hard timeout|hard turn|hard file|prompt soft)\b",
    r"\b(?:budget|timeout|turn|file|limit|manual fallback|hard timeout|hard turn|hard file|prompt soft)\b.{0,48}\b(?:not configured|missing|absent|unavailable|required but missing)\b",
    r"(?:无|没有|未设置|缺少).{0,24}(?:预算|超时|轮次|文件|限制)",
)
ALLOWED_ACTION_TERMS = ("read", "rg", "git diff", "git status")
PROHIBITED_ACTION_TERMS = (
    "write",
    "edit",
    "task_plan",
    "progress",
    "findings",
    "source",
    "deploy",
    "db write",
    "commit",
    "push",
    "secrets",
    "new state source",
)
GENERIC_EVIDENCE_MARKERS = {
    "summary",
    "summary only",
    "pass summary",
    "see above",
    "none",
    "not-needed",
    "not needed",
    "n/a",
    "na",
    "待填写",
}
EVIDENCE_BINDING_TERMS = (
    ".agent-state/runs/",
    "review evidence index",
    "evidence-ledger.md",
    "diff.patch",
    "changed-files.txt",
    "waivers.md",
    "dirty-worktree-summary.json",
    "release-source",
    "artifact",
    "stdout",
    "stderr",
)
LINK_PLACEHOLDER_VALUES = {
    "",
    "none",
    "n/a",
    "na",
    "not-needed",
    "not needed",
    "not-applicable",
    "not_applicable",
    "optional",
    "pending",
    "missing",
    "待填写",
}
FORBIDDEN_ALLOWED_ACTION_TERMS = (
    "write",
    "edit",
    "task_plan",
    "progress",
    "findings",
    "source changes",
    "deploy",
    "db write",
    "database write",
    "commit",
    "push",
    "secret",
    "secrets",
    "new state source",
)
PLACEHOLDER_MARKERS = (
    "待填写",
    "<run_id>",
    "iso-8601",
    "commit sha /",
    "sha256 of",
    "main codex / tooling",
)

SECRET_PATTERNS = (
    re.compile(r"(?im)^\s*authorization\s*:\s*(bearer|basic)\s+\S+"),
    re.compile(r"(?im)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?im)^\s*(api[_-]?key|secret|token|password|private[_-]?key)\s*=\s*\S+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
)

SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
STRUCTURAL_INDEX_RAW_MARKERS = (
    ".codegraph/",
    "codegraph-out/",
    "graphify-out/graph.json",
    "graphify-out/graph.html",
    "graph.json",
    "graph.html",
    "/graph.json",
    "/graph.html",
)
CHECK_ID_RE = re.compile(r"\bC\d+\b")
EVIDENCE_PATH_RE = re.compile(
    r"\b([A-Za-z0-9._/-]+\.(?:md|json|txt|log|patch|diff|html|png|jpg|jpeg|webp|xml|yaml|yml))(?:[:#][A-Za-z0-9_.-]+)?\b"
)


def is_forbidden_name(path: Path) -> bool:
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.") or name.endswith(".har") or name.endswith(".trace")


def is_forbidden_structural_index_artifact(rel: Path) -> bool:
    normalized = rel.as_posix().lower()
    return any(marker in normalized for marker in STRUCTURAL_INDEX_RAW_MARKERS)


def scan_text(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return [f"{path.name}: cannot read file: {exc}"]

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path.name}: contains unredacted secret-like content")
            break
    return errors


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def is_placeholder_value(value: str, allow_not_needed: bool = False) -> bool:
    normalized = clean_cell(value).lower()
    if not normalized:
        return True
    if allow_not_needed and normalized == "not-needed":
        return False
    if normalized in {"pending", "missing", "required"}:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def is_link_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    return normalized in LINK_PLACEHOLDER_VALUES or any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def review_evidence_rows(packet: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for candidate in (packet / "review-packet.md", packet / "evidence-ledger.md"):
        if candidate.is_file():
            rows.extend(extract_table(candidate.read_text(encoding="utf-8", errors="ignore"), "## Review Evidence Index"))
    return rows


def declared_evidence_bindings(packet: Path) -> tuple[set[str], set[str]]:
    check_ids: set[str] = set()
    paths: set[str] = set()
    for row in review_evidence_rows(packet):
        check_id = clean_cell(row.get("check_id", ""))
        if check_id and not is_placeholder_value(check_id):
            check_ids.add(check_id)
        for field in ("artifact_path", "stdout_stderr_summary_path"):
            value = clean_cell(row.get(field, ""))
            if value and not is_placeholder_value(value, allow_not_needed=True):
                paths.add(value)
    return check_ids, paths


def evidence_binding_errors(
    evidence: str,
    packet: Path,
    *,
    subject: str = "accepted finding evidence",
) -> list[str]:
    normalized = clean_cell(evidence).lower()
    if normalized in GENERIC_EVIDENCE_MARKERS:
        return [f"{subject} must reference a declared check_id, packet file, or artifact path"]
    if any(marker in normalized for marker in ("summary only", "pass summary", "see above", "not-needed", "not needed", "待填写")):
        return [f"{subject} must reference a declared check_id, packet file, or artifact path"]

    check_ids, declared_paths = declared_evidence_bindings(packet)
    errors: list[str] = []
    matched = False
    for check_id in CHECK_ID_RE.findall(evidence):
        matched = True
        if check_id not in check_ids:
            errors.append(f"unknown check_id {check_id}")

    for path_ref in EVIDENCE_PATH_RE.findall(evidence):
        matched = True
        if path_ref in declared_paths:
            continue
        if (packet / path_ref).is_file():
            continue
        errors.append(f"evidence file does not exist or is not declared: {path_ref}")

    for filename in REQUIRED_FILES + ("role-review-result.json", "role-review-scenario-packet.md"):
        if filename.lower() in normalized and (packet / filename).exists():
            matched = True

    if not matched:
        errors.append(f"{subject} must reference a declared check_id, packet file, or artifact path")
    return errors


def evidence_has_binding(evidence: str, packet: Path) -> bool:
    return not evidence_binding_errors(evidence, packet)


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


def extract_table(markdown_text: str, heading: str, *, strict: bool = False) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=strict,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def malformed_table_error(filename: str, heading: str, exc: md_table.MarkdownTableError) -> str:
    return f"{filename}: {heading.removeprefix('## ')} table is malformed: {exc}"


def validate_review_evidence_index(packet: Path, strict: bool) -> list[str]:
    errors: list[str] = []
    candidates = (packet / "review-packet.md", packet / "evidence-ledger.md")
    rows: list[dict[str, str]] = []
    source_name = ""
    for candidate in candidates:
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8", errors="ignore")
        candidate_rows = extract_table(text, "## Review Evidence Index")
        if candidate_rows:
            rows = candidate_rows
            source_name = candidate.name
            break

    if not rows and strict:
        return ["review evidence index: missing ## Review Evidence Index table with raw command evidence fields"]
    if not rows:
        return []

    first_row = rows[0]
    missing_fields = [field for field in REVIEW_EVIDENCE_FIELDS if field not in first_row]
    if missing_fields:
        errors.append(f"review evidence index: missing required fields: {', '.join(missing_fields)}")
        return errors

    real_rows = [row for row in rows if not is_placeholder_value(row.get("check_id", ""))]
    if not real_rows:
        errors.append(f"{source_name}: Review Evidence Index has no real check rows")
        return errors

    for row in real_rows:
        check_id = clean_cell(row.get("check_id", "unknown"))
        for field in REVIEW_EVIDENCE_FIELDS:
            allow_not_needed = field == "waiver_id"
            if is_placeholder_value(row.get(field, ""), allow_not_needed=allow_not_needed):
                errors.append(f"{source_name}: Review Evidence Index {check_id}: {field} is missing")
    return errors


def validate_scenario_snapshot_metadata(packet: Path) -> list[str]:
    snapshot = packet / "role-review-scenario-packet.md"
    if not snapshot.exists():
        return []
    text = snapshot.read_text(encoding="utf-8", errors="ignore")
    try:
        rows = extract_table(text, "## Snapshot Metadata", strict=True)
    except md_table.MarkdownTableError as exc:
        return [malformed_table_error(snapshot.name, "## Snapshot Metadata", exc)]
    if not rows:
        return ["role-review-scenario-packet.md: missing Snapshot Metadata table"]

    metadata = {normalize_key(row.get("field", "")): row.get("value", "") for row in rows}
    errors: list[str] = []
    for field in SCENARIO_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"role-review-scenario-packet.md: Snapshot Metadata missing {field}")
            continue
        if is_placeholder_value(metadata[field]):
            errors.append(f"role-review-scenario-packet.md: Snapshot Metadata {field} is missing")

    source_sha256 = clean_cell(metadata.get("source_sha256", ""))
    if source_sha256 and not is_placeholder_value(source_sha256) and not SHA256_RE.fullmatch(source_sha256):
        errors.append("role-review-scenario-packet.md: source_sha256 must be 64 hex characters")

    if clean_cell(metadata.get("readonly_snapshot", "")).lower() != "true":
        errors.append("role-review-scenario-packet.md: readonly_snapshot must be true")
    if clean_cell(metadata.get("authoritative_source", "")).lower() != "task_plan.md":
        errors.append("role-review-scenario-packet.md: authoritative_source must be task_plan.md")
    return errors


def normalize_policy_text(value: str) -> str:
    return clean_cell(value).lower().replace("-", " ").replace("/", " ")


def normalize_brief_value(value: str) -> str:
    return clean_cell(value).lower().replace("_", "-")


def normalize_search_text(value: str) -> str:
    return clean_cell(value).lower().replace("-", " ").replace("_", " ")


def has_budget_negation(value: str) -> bool:
    normalized = normalize_search_text(value)
    return any(re.search(pattern, normalized) for pattern in BUDGET_NEGATION_PATTERNS)


def has_runtime_budget(value: str) -> bool:
    normalized = normalize_search_text(value)
    if has_budget_negation(normalized):
        return False
    return any(term in normalized or term.replace("-", " ") in normalized for term in VALID_RUNTIME_BUDGET_TERMS)


def validate_agent_brief(packet: Path, strict: bool) -> list[str]:
    review_packet = packet / "review-packet.md"
    if not review_packet.is_file():
        return []
    text = review_packet.read_text(encoding="utf-8", errors="ignore")
    try:
        rows = extract_table(text, "## Agent Brief", strict=True)
    except md_table.MarkdownTableError as exc:
        return [malformed_table_error(review_packet.name, "## Agent Brief", exc)]
    if not rows:
        if strict:
            return ["review-packet.md: missing ## Agent Brief table"]
        return []

    brief = {normalize_key(row.get("field", "")): row.get("value", "") for row in rows}
    errors: list[str] = []
    for field in AGENT_BRIEF_FIELDS:
        if field not in brief:
            errors.append(f"review-packet.md: Agent Brief missing {field}")
            continue
        if is_placeholder_value(brief[field]):
            errors.append(f"review-packet.md: Agent Brief {field} is missing")

    role = normalize_brief_value(brief.get("role", ""))
    if role and not is_placeholder_value(role) and role not in VALID_AGENT_ROLES:
        errors.append(f"review-packet.md: Agent Brief role is invalid: {role}")

    task_class = normalize_brief_value(brief.get("task_class", ""))
    if task_class and not is_placeholder_value(task_class):
        if task_class not in VALID_TASK_CLASSES:
            errors.append(f"review-packet.md: Agent Brief task_class is invalid: {task_class}")
        elif task_class == "scoped-implementation":
            errors.append("review-packet.md: Agent Brief task_class scoped-implementation is not allowed for read-only policy-auto reviewers")

    context = normalize_search_text(brief.get("context", ""))
    full_history_terms = (
        "complete chat history",
        "full chat history included",
        "full chat transcript",
        "完整聊天记录",
        "完整对话历史",
        "全部聊天历史",
    )
    if any(term in context for term in full_history_terms):
        errors.append("review-packet.md: Agent Brief context must not include full chat history")

    ownership = normalize_brief_value(brief.get("ownership", ""))
    if ownership and not is_placeholder_value(ownership) and ownership not in READ_ONLY_OWNERSHIPS:
        errors.append("review-packet.md: Agent Brief ownership must be finding-only or no-state-ownership")

    output_format = normalize_search_text(brief.get("output_format", ""))
    for term in OUTPUT_FORMAT_TERMS:
        normalized_term = term.replace("_", " ")
        if normalized_term not in output_format:
            errors.append(f"review-packet.md: Agent Brief output_format must include {term}")

    stop_condition = normalize_search_text(brief.get("stop_condition", ""))
    if stop_condition and not is_placeholder_value(stop_condition):
        if not any(term in stop_condition for term in STOP_CONDITION_TERMS):
            errors.append("review-packet.md: Agent Brief stop_condition must include max files/time/findings, packet insufficient, or secret suspicion")
        if stop_condition in {"finish review", "complete review", "done", "review complete"}:
            errors.append("review-packet.md: Agent Brief stop_condition is too vague")
    return errors


def validate_reviewer_policy(packet: Path) -> list[str]:
    review_packet = packet / "review-packet.md"
    if not review_packet.is_file():
        return []
    text = review_packet.read_text(encoding="utf-8", errors="ignore")
    try:
        rows = extract_table(text, "## Reviewer Policy", strict=True)
    except md_table.MarkdownTableError as exc:
        return [malformed_table_error(review_packet.name, "## Reviewer Policy", exc)]
    if not rows:
        return ["review-packet.md: missing ## Reviewer Policy table"]

    policy = {normalize_key(row.get("field", "")): row.get("value", "") for row in rows}
    errors: list[str] = []
    for field in REVIEWER_POLICY_FIELDS:
        if field not in policy:
            errors.append(f"review-packet.md: Reviewer Policy missing {field}")
            continue
        if is_placeholder_value(policy[field]):
            errors.append(f"review-packet.md: Reviewer Policy {field} is missing")

    repo_write_scope = ""
    if "repo_write_scope" in policy:
        repo_write_scope = normalize_policy_text(policy.get("repo_write_scope", ""))
    elif "write_scope" in policy:
        repo_write_scope = normalize_policy_text(policy.get("write_scope", ""))
    else:
        errors.append("review-packet.md: Reviewer Policy missing repo_write_scope")
    if repo_write_scope and repo_write_scope != "none":
        errors.append("review-packet.md: Reviewer Policy repo_write_scope/write_scope must be none")

    artifact_write_scope = normalize_policy_text(policy.get("artifact_write_scope", ""))
    allowed_artifact_write_scopes = (
        "none",
        "runner managed result only under packet",
        "result artifact only under packet",
    )
    if artifact_write_scope and not any(allowed == artifact_write_scope or allowed in artifact_write_scope for allowed in allowed_artifact_write_scopes):
        errors.append("review-packet.md: Reviewer Policy artifact_write_scope must be none or packet-scoped result artifact only")

    allowed_actions = normalize_policy_text(policy.get("allowed_actions", ""))
    for term in ALLOWED_ACTION_TERMS:
        if term not in allowed_actions:
            errors.append(f"review-packet.md: Reviewer Policy allowed_actions must include {term}")
    forbidden_allowed = [term for term in FORBIDDEN_ALLOWED_ACTION_TERMS if term in allowed_actions]
    if forbidden_allowed:
        errors.append(
            "review-packet.md: Reviewer Policy allowed_actions must not include prohibited actions: "
            + ", ".join(sorted(set(forbidden_allowed)))
        )

    prohibited_actions = normalize_policy_text(policy.get("prohibited_actions", ""))
    for term in PROHIBITED_ACTION_TERMS:
        if term not in prohibited_actions:
            errors.append(f"review-packet.md: Reviewer Policy prohibited_actions must include {term}")

    state_source_policy = normalize_policy_text(policy.get("state_source_policy", ""))
    state_terms = ("second state source", "new state source", "second", "new")
    denial_terms = ("no", "forbid", "forbidden", "must not", "do not", "not ", "禁止", "不得", "不能")
    if state_source_policy:
        has_state_term = any(term in state_source_policy for term in state_terms)
        has_denial = any(term in state_source_policy for term in denial_terms)
        if not (has_state_term and has_denial):
            errors.append("review-packet.md: Reviewer Policy state_source_policy must explicitly forbid second/new state sources")

    subdelegation = normalize_policy_text(policy.get("subdelegation", ""))
    if subdelegation and subdelegation != "none":
        errors.append("review-packet.md: Reviewer Policy subdelegation must be none")
    return errors


def validate_reviewer_execution_metadata(packet: Path, strict: bool) -> list[str]:
    review_packet = packet / "review-packet.md"
    if not review_packet.is_file():
        return []
    text = review_packet.read_text(encoding="utf-8", errors="ignore")
    try:
        rows = extract_table(text, "## Reviewer Execution Metadata", strict=True)
    except md_table.MarkdownTableError as exc:
        return [malformed_table_error(review_packet.name, "## Reviewer Execution Metadata", exc)]
    if not rows:
        if strict:
            return ["review-packet.md: missing ## Reviewer Execution Metadata table"]
        return []

    metadata = {normalize_key(row.get("field", "")): row.get("value", "") for row in rows}
    errors: list[str] = []
    for field in EXECUTION_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"review-packet.md: Reviewer Execution Metadata missing {field}")
            continue
        value = normalize_search_text(metadata[field])
        if is_placeholder_value(value):
            errors.append(f"review-packet.md: Reviewer Execution Metadata {field} is missing")
        elif strict and value in {"not-needed", "not needed"}:
            errors.append(f"review-packet.md: Reviewer Execution Metadata {field} cannot be not-needed in strict/high/release mode")
        elif not has_runtime_budget(value):
            errors.append(f"review-packet.md: Reviewer Execution Metadata {field} must identify hard timeout/turn/file limits, prompt-soft-limit, manual-fallback, or not-needed")
    return errors


def validate_output_contract(packet: Path, strict: bool) -> list[str]:
    review_packet = packet / "review-packet.md"
    if not review_packet.is_file():
        return []

    text = review_packet.read_text(encoding="utf-8", errors="ignore")
    section = extract_section(text, "## Output Contract")
    if not section:
        if strict:
            return ["review-packet.md: missing ## Output Contract section"]
        return []

    normalized_section = normalize_search_text("\n".join(section))
    errors: list[str] = []
    for field in OUTPUT_CONTRACT_FIELDS:
        normalized_field = field.replace("_", " ")
        if normalized_field not in normalized_section:
            errors.append(f"review-packet.md: Output Contract missing {field}")
    return errors


def validate_findings(packet: Path) -> list[str]:
    findings = packet / "findings.json"
    if not findings.exists():
        return []
    try:
        payload = json.loads(findings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"findings.json: invalid JSON: {exc.msg}"]

    rows = payload.get("findings", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        return ["findings.json: expected a list or an object with findings list"]

    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"findings.json[{index}]: finding must be an object")
            continue
        finding_id = row.get("finding_id") or f"#{index}"
        severity = str(row.get("severity", "")).upper()
        evidence_level = str(row.get("evidence_level", "")).lower()
        evidence = str(row.get("evidence", "")).strip()
        if severity and severity not in SEVERITIES:
            errors.append(f"finding {finding_id}: severity must be S0/S1/S2/S3")
        if evidence_level not in EVIDENCE_LEVELS:
            errors.append(f"finding {finding_id}: evidence_level must be direct/indirect/unverified")
        if not evidence:
            errors.append(f"finding {finding_id}: evidence is missing")
        if severity in {"S0", "S1"} and evidence_level != "direct":
            errors.append(f"finding {finding_id}: S0/S1 findings require direct evidence")
    return errors


def validate_role_review_result(packet: Path) -> list[str]:
    result_path = packet / "role-review-result.json"
    if not result_path.exists():
        return []
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"role-review-result.json: invalid JSON: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["role-review-result.json: expected an object"]

    errors: list[str] = []
    role = normalize_brief_value(str(payload.get("role", "")))
    verdict = normalize_brief_value(str(payload.get("verdict", "")))
    review_packet = packet / "review-packet.md"
    if review_packet.is_file():
        brief_rows = extract_table(review_packet.read_text(encoding="utf-8", errors="ignore"), "## Agent Brief")
        brief = {normalize_key(row.get("field", "")): row.get("value", "") for row in brief_rows}
        brief_role = normalize_brief_value(brief.get("role", ""))
        if brief_role and role != brief_role:
            errors.append("role-review-result.json: role must match Agent Brief role")
    if role not in VALID_AGENT_ROLES:
        errors.append("role-review-result.json: role must match a valid Agent Brief role")
    if verdict not in VERDICTS:
        errors.append("role-review-result.json: verdict must be pass/needs-more-evidence/blocking/review-incomplete/review-unverified")
    errors.extend(
        validate_falsification_attempts(
            payload,
            context="role-review-result.json",
            evidence_errors=lambda evidence: evidence_binding_errors(
                evidence,
                packet,
                subject="falsification attempt evidence",
            ),
        )
    )

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        errors.append("role-review-result.json: findings must be a list")
        return errors

    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            errors.append(f"role-review-result.json[{index}]: finding must be an object")
            continue
        finding_id = str(finding.get("finding_id", f"#{index}"))
        severity = str(finding.get("severity", "")).upper()
        evidence_level = str(finding.get("evidence_level", "")).lower()
        linked_acceptance_id = str(finding.get("linked_acceptance_id", "")).strip()
        linked_scenario_id = str(finding.get("linked_scenario_id", "")).strip()
        linked_slice_id = str(finding.get("linked_slice_id", "")).strip()
        case_class = str(finding.get("case_class", "")).strip()
        claim = str(finding.get("claim", "")).strip()
        evidence = str(finding.get("evidence", "")).strip()
        disposition_value = finding.get("recommended_disposition", finding.get("suggested_disposition", ""))
        disposition = normalize_brief_value(str(disposition_value))
        if "recommended_disposition" not in finding and "suggested_disposition" not in finding:
            errors.append(f"role-review-result.json finding {finding_id}: recommended_disposition is missing")
        if not linked_acceptance_id:
            errors.append(f"role-review-result.json finding {finding_id}: linked_acceptance_id is missing")
        if not linked_scenario_id:
            errors.append(f"role-review-result.json finding {finding_id}: linked_scenario_id is missing")
        if not linked_slice_id:
            errors.append(f"role-review-result.json finding {finding_id}: linked_slice_id is missing")
        if not case_class:
            errors.append(f"role-review-result.json finding {finding_id}: case_class is missing")
        if not claim:
            errors.append(f"role-review-result.json finding {finding_id}: claim is missing")
        if severity not in SEVERITIES:
            errors.append(f"role-review-result.json finding {finding_id}: severity must be S0/S1/S2/S3")
        if evidence_level not in EVIDENCE_LEVELS:
            errors.append(f"role-review-result.json finding {finding_id}: evidence_level must be direct/indirect/unverified")
        if not evidence:
            errors.append(f"role-review-result.json finding {finding_id}: evidence is missing")
        if severity in {"S0", "S1"} and evidence_level != "direct":
            errors.append(f"role-review-result.json finding {finding_id}: S0/S1 findings require direct evidence")
        if disposition and disposition not in DISPOSITIONS:
            errors.append(f"role-review-result.json finding {finding_id}: recommended_disposition is invalid")
        if disposition == "accepted":
            for field_name, linked_value in (
                ("linked_acceptance_id", linked_acceptance_id),
                ("linked_scenario_id", linked_scenario_id),
                ("linked_slice_id", linked_slice_id),
            ):
                if is_link_placeholder(linked_value):
                    errors.append(f"role-review-result.json finding {finding_id}: accepted finding requires {field_name}")
            for binding_error in evidence_binding_errors(evidence, packet):
                errors.append(f"role-review-result.json finding {finding_id}: {binding_error}")
    return errors


def validate(packet: Path, strict_evidence: bool = False, require_result: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not packet.is_dir():
        return {"status": "fail", "errors": [f"packet directory not found: {packet}"], "warnings": []}

    for filename in REQUIRED_FILES:
        path = packet / filename
        if not path.is_file():
            errors.append(f"missing required packet file: {filename}")
        elif path.stat().st_size == 0:
            errors.append(f"packet file is empty: {filename}")

    dirty_summary = packet / "dirty-worktree-summary.json"
    if dirty_summary.is_file():
        try:
            json.loads(dirty_summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"dirty-worktree-summary.json: invalid JSON: {exc.msg}")

    for path in packet.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(packet)
        if is_forbidden_name(path):
            errors.append(f"forbidden raw sensitive artifact in packet: {rel}")
        if is_forbidden_structural_index_artifact(rel):
            errors.append(f"forbidden raw structural index artifact in packet: {rel}")
        if path.stat().st_size > 512 * 1024:
            message = f"large packet file must be summarized before review: {rel}"
            if strict_evidence:
                errors.append(message)
            else:
                warnings.append(message)
            continue
        errors.extend(scan_text(path))

    if require_result and not (packet / "role-review-result.json").is_file():
        errors.append("missing required reviewer result artifact: role-review-result.json")

    errors.extend(validate_findings(packet))
    errors.extend(validate_role_review_result(packet))
    errors.extend(validate_agent_brief(packet, strict=strict_evidence))
    errors.extend(validate_reviewer_policy(packet))
    errors.extend(validate_reviewer_execution_metadata(packet, strict=strict_evidence))
    errors.extend(validate_output_contract(packet, strict=strict_evidence))
    errors.extend(validate_review_evidence_index(packet, strict=strict_evidence))
    errors.extend(validate_scenario_snapshot_metadata(packet))

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "strict_evidence": strict_evidence,
        "require_result": require_result,
        "required_files": list(REQUIRED_FILES),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate isolated / role review packet structure and redaction.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--packet", required=True, help="Review packet directory.")
    parser.add_argument("--strict", action="store_true", help="Require replayable Review Evidence Index fields.")
    parser.add_argument(
        "--risk-tier",
        choices=("low", "standard", "high", "release"),
        default=None,
        help="Optional task risk tier. high/release imply --strict evidence checks.",
    )
    parser.add_argument(
        "--require-result",
        action="store_true",
        help="Require role-review-result.json. Use after a reviewer has actually started; do not use for pre-start packet validation.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    packet = Path(args.packet)
    if not packet.is_absolute():
        packet = root / packet

    strict_evidence = args.strict or args.risk_tier in {"high", "release"}
    payload = validate(packet, strict_evidence=strict_evidence, require_result=args.require_result)
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
