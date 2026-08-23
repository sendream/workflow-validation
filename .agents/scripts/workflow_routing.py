#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

import markdown_table as md


VALID_RISK_TIERS = ("low", "standard", "high", "release")
VALID_IMPACT_SCOPES = ("visible", "file-linked", "cross-package", "external-system")
HIGH_RISK_TIERS = {"high", "release"}
RISK_TIER_RANK = {value: index for index, value in enumerate(VALID_RISK_TIERS)}
IMPACT_SCOPE_RANK = {value: index for index, value in enumerate(VALID_IMPACT_SCOPES)}
ROUTING_HEADINGS = ("Workflow Routing", "Risk Tier", "Impact Scope")
SOURCE_ROOT_REGISTRY_HEADING = "Source Root Registry"

# Shared workflow enums. Validators import these constants so Markdown prompts,
# templates, and deterministic checks do not grow separate state machines.
FINAL_EVIDENCE_STATUSES = {"PASS", "MANUAL", "WAIVED", "FAILED", "BLOCKED", "NOT_APPLICABLE"}
CLOSEOUT_ALLOWED_FINAL_STATUSES = {"PASS", "MANUAL", "WAIVED", "NOT_APPLICABLE"}
WAIVER_ALLOWED_TO_SHIP = {"yes", "no", "conditional"}
WAIVER_ALLOWED_TO_CONTINUE = {"yes", "conditional"}
RELEASE_SOURCE_MODES = {
    "clean-source-build",
    "source-manifest-build",
    "allowed-diff-build",
    "blocked",
    "not-needed",
}
EVIDENCE_REF_TYPES = {
    "run",
    "manifest",
    "artifact",
    "release-source",
    "source-file",
    "commit-ref",
    "push-ref",
    "waiver",
    "manual",
}

REVIEWER_TRIGGER_DECISIONS = {"not-needed", "assessment-only", "preferred"}
REVIEWER_LEGACY_TRIGGER_DECISIONS = {
    "started",
    "unavailable",
    "incomplete",
    "not-authorized",
    "reviewer-unavailable",
    "review-incomplete",
    "runtime-policy-blocked",
    "explicit-delegation-required",
    "packet-invalid",
    "brief-invalid",
}
REVIEWER_AUTHORIZED_SCOPES = {"policy-auto", "task", "session", "external-standing-opt-in"}
REVIEWER_AUTH_SCOPES = {"none", *REVIEWER_AUTHORIZED_SCOPES, "revoked", "not-needed"}
REVIEWER_START_RESULTS = {
    "started",
    "unavailable",
    "incomplete",
    "not-needed",
    "not-authorized",
    "packet-invalid",
    "brief-invalid",
    "policy-auto-started",
    "task-authorized-started",
    "session-authorized-started",
    "external-opt-in-started",
    "runtime-policy-blocked",
    "explicit-delegation-required",
    "tool-unavailable",
    "validator-failed",
    "review-incomplete",
    "reviewer-timeout",
    "budget-exceeded",
    "explicit-denied",
}
REVIEWER_STARTED_RESULTS = {
    "started",
    "policy-auto-started",
    "task-authorized-started",
    "session-authorized-started",
    "external-opt-in-started",
}
REVIEWER_UNAVAILABLE_RESULTS = {"unavailable", "tool-unavailable", "runtime-policy-blocked", "explicit-delegation-required"}
REVIEWER_INCOMPLETE_RESULTS = {"incomplete", "review-incomplete", "reviewer-timeout", "budget-exceeded"}
REVIEWER_DENIED_RESULTS = {"not-authorized", "explicit-denied"}
REVIEWER_INVALID_PACKET_RESULTS = {"packet-invalid", "brief-invalid", "validator-failed"}
REVIEWER_LEGACY_STRICT_START_RESULTS = {"started", "unavailable", "incomplete", "not-authorized"}
REVIEWER_AUTHORITY_MODES = {"policy-auto", "task-authorized", "session-authorized", "external-standing-opt-in", "not-needed"}
_REVIEWER_TABLE_VALUE_RE = re.compile(
    r"(?im)^\|\s*(?P<item>Required assessment|Trigger decision|Start required|Start result)\s*\|\s*(?P<value>[^|]+)\|"
)
_NARRATIVE_REVIEWER_CLAIM_RE = re.compile(
    r"\b(reviewer|subagent)\b.{0,40}\b(passed|complete|approved|done)\b",
    re.IGNORECASE,
)


def reviewer_route_requested(progress_text: str) -> bool:
    """True only when a real G16 / reviewer signal exists, not merely high/release."""
    text = progress_text or ""
    if "role-review/" in text:
        return True
    if _NARRATIVE_REVIEWER_CLAIM_RE.search(text):
        return True
    values: dict[str, str] = {}
    for match in _REVIEWER_TABLE_VALUE_RE.finditer(text):
        values[match.group("item").strip().lower()] = match.group("value").strip().lower()
    if values.get("required assessment") == "yes":
        return True
    if values.get("trigger decision") == "preferred":
        return True
    if values.get("start required") == "yes":
        return True
    if values.get("start result") in REVIEWER_STARTED_RESULTS:
        return True
    return False


@dataclass(frozen=True)
class RoutingField:
    value: str
    source_heading: str
    source_key: str
    source_value: str


@dataclass(frozen=True)
class TaskRouting:
    risk_tier: RoutingField | None
    impact_scope: RoutingField | None


@dataclass(frozen=True)
class SourceRoot:
    root_id: str
    repo_id: str
    vcs_root: str
    source_root: str
    status: str
    evidence_scope: str
    structural_index_provider: str
    refresh_when: str


@dataclass(frozen=True)
class EvidenceRef:
    ref_type: str
    target: str
    root_id: str | None
    path: str | None
    raw: str


def clean_cell(value: str) -> str:
    return md.clean_cell(value)


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", clean_cell(value)).lower()


def extract_section(markdown_text: str, heading: str) -> list[str]:
    wanted = normalize_heading(heading)
    lines = markdown_text.splitlines()
    in_section = False
    section_level = 0
    section: list[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            title = normalize_heading(heading_match.group(2))
            if in_section and level <= section_level:
                break
            if title == wanted:
                in_section = True
                section_level = level
                continue
        if in_section:
            section.append(line)
    return section


def section_text(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading))


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    section = "\n".join(extract_section(markdown_text, heading))
    rows: list[dict[str, str]] = []

    for table in md.parse_markdown_tables(section, strict=False):
        header = [normalize_key(cell) for cell in table.headers]
        for cells in table.rows:
            if len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))
    if rows:
        return rows

    # Backward-compatible routing only: older task files sometimes used
    # pipe-shaped key/value tables without a Markdown separator row.
    pipe_lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    if len(pipe_lines) < 2:
        return rows
    header = [normalize_key(cell) for cell in md.split_markdown_table_row(pipe_lines[0])]
    for line in pipe_lines[1:]:
        cells = md.split_markdown_table_row(line)
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def parse_source_root_registry(markdown_text: str) -> dict[str, SourceRoot]:
    roots: dict[str, SourceRoot] = {}
    for row in extract_table(markdown_text, SOURCE_ROOT_REGISTRY_HEADING):
        root_id = clean_cell(row.get("root_id", "") or row.get("id", ""))
        if not root_id or root_id.lower() in {"not-needed", "待填写", "none"}:
            continue
        source_root = clean_cell(row.get("source_root", "") or row.get("path", ""))
        if not source_root:
            continue
        roots[root_id] = SourceRoot(
            root_id=root_id,
            repo_id=clean_cell(row.get("repo_id", "")),
            vcs_root=clean_cell(row.get("vcs_root", "")),
            source_root=source_root,
            status=clean_cell(row.get("status", "")),
            evidence_scope=clean_cell(row.get("evidence_scope", "")),
            structural_index_provider=clean_cell(row.get("structural_index_provider", "")),
            refresh_when=clean_cell(row.get("refresh_when", "")),
        )
    return roots


def parse_evidence_ref(value: str) -> EvidenceRef | None:
    raw = clean_cell(value)
    if not raw or ":" not in raw:
        return None
    ref_type, rest = raw.split(":", 1)
    ref_type = ref_type.strip().lower().replace("_", "-")
    rest = rest.strip()
    if ref_type not in EVIDENCE_REF_TYPES or not rest:
        return None
    root_id: str | None = None
    path: str | None = None
    if ref_type == "source-file":
        if ":" not in rest:
            return EvidenceRef(ref_type=ref_type, target=rest, root_id=None, path=None, raw=raw)
        root_id, path = rest.split(":", 1)
        root_id = clean_cell(root_id)
        path = clean_cell(path)
        if not root_id or not path:
            return EvidenceRef(ref_type=ref_type, target=rest, root_id=root_id or None, path=path or None, raw=raw)
        posix = PurePosixPath(path)
        if posix.is_absolute() or ".." in posix.parts:
            return EvidenceRef(ref_type=ref_type, target=rest, root_id=root_id, path=path, raw=raw)
    return EvidenceRef(ref_type=ref_type, target=rest, root_id=root_id, path=path, raw=raw)


def _field_key(raw_key: str, heading: str) -> str | None:
    key = normalize_key(raw_key)
    normalized_heading = normalize_heading(heading)
    if key in {"risk_tier", "risk", "risk_level"}:
        return "risk_tier"
    if key == "tier" and normalized_heading == "risk tier":
        return "risk_tier"
    if key in {"impact_scope", "impact", "scope"}:
        return "impact_scope"
    if key == "scope" and normalized_heading == "impact scope":
        return "impact_scope"
    return None


def _bare_enum_from_value(value: str, allowed: tuple[str, ...]) -> str | None:
    normalized = clean_cell(value).lower()
    if not normalized:
        return None
    normalized = re.sub(r"^`(?P<token>[a-z]+(?:-[a-z]+)*)`(?P<rest>\s*(?:$|[(/,;#:-]).*)", r"\g<token>\g<rest>", normalized)
    normalized = normalized.strip("`")
    hits = [token for token in re.findall(r"[a-z]+(?:-[a-z]+)*", normalized) if token in allowed]
    if len(set(hits)) != 1:
        return None
    token_match = re.match(r"^(?P<token>[a-z]+(?:-[a-z]+)*)(?P<rest>\s*(?:$|[(/,;#:-]))", normalized)
    if not token_match:
        return None
    token = token_match.group("token")
    if token not in allowed:
        return None
    rest = normalized[token_match.end("token") :].strip()
    if not rest:
        return token
    if not re.match(r"^(?:[/,;#:-]|\(|（)", rest):
        return None
    return token


def _line_fields(markdown_text: str, heading: str) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for line in extract_section(markdown_text, heading):
        match = re.match(
            r"^\s*(?:[-*]\s*)?(?P<key>[A-Za-z][A-Za-z _/-]{0,48})\s*[:：=]\s*(?P<value>.+?)\s*$",
            line,
        )
        if match:
            field = _field_key(match.group("key"), heading)
            if field:
                fields.append((field, clean_cell(match.group("value"))))
                continue

        bare = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if normalize_heading(heading) == "risk tier" and _bare_enum_from_value(bare, VALID_RISK_TIERS):
            fields.append(("risk_tier", bare))
        if normalize_heading(heading) == "impact scope" and _bare_enum_from_value(bare, VALID_IMPACT_SCOPES):
            fields.append(("impact_scope", bare))
    return fields


def _table_fields(markdown_text: str, heading: str) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for row in extract_table(markdown_text, heading):
        for key, value in row.items():
            field = _field_key(key, heading)
            if field:
                fields.append((field, value))

        row_key = (
            row.get("item", "")
            or row.get("field", "")
            or row.get("key", "")
            or row.get("check", "")
            or row.get("name", "")
        )
        row_value = row.get("value", "") or row.get("status", "") or row.get("decision", "")
        field = _field_key(row_key, heading)
        if field and row_value:
            fields.append((field, row_value))
    return fields


def _most_conservative(candidates: list[RoutingField], ranks: dict[str, int]) -> RoutingField | None:
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: ranks[candidate.value])


def parse_task_routing(markdown_text: str) -> TaskRouting:
    risk_candidates: list[RoutingField] = []
    impact_candidates: list[RoutingField] = []

    for heading in ROUTING_HEADINGS:
        for field, raw_value in (*_line_fields(markdown_text, heading), *_table_fields(markdown_text, heading)):
            if field == "risk_tier":
                value = _bare_enum_from_value(raw_value, VALID_RISK_TIERS)
                if value:
                    risk_candidates.append(RoutingField(value=value, source_heading=heading, source_key=field, source_value=raw_value))
            if field == "impact_scope":
                value = _bare_enum_from_value(raw_value, VALID_IMPACT_SCOPES)
                if value:
                    impact_candidates.append(RoutingField(value=value, source_heading=heading, source_key=field, source_value=raw_value))
    risk = _most_conservative(risk_candidates, RISK_TIER_RANK)
    impact = _most_conservative(impact_candidates, IMPACT_SCOPE_RANK)
    return TaskRouting(risk_tier=risk, impact_scope=impact)


def extract_risk_tier(markdown_text: str) -> str | None:
    routing = parse_task_routing(markdown_text)
    return routing.risk_tier.value if routing.risk_tier is not None else None


def risk_tier_or_unknown(markdown_text: str) -> str:
    return extract_risk_tier(markdown_text) or "unknown"


def extract_impact_scope(markdown_text: str) -> str | None:
    routing = parse_task_routing(markdown_text)
    return routing.impact_scope.value if routing.impact_scope is not None else None


def has_external_system_scope(markdown_text: str) -> bool:
    return extract_impact_scope(markdown_text) == "external-system"


def is_high_or_release(value: str | None) -> bool:
    return (value or "").strip().lower() in HIGH_RISK_TIERS


def is_release_source_mode(value: str | None) -> bool:
    return (value or "").strip().lower() in RELEASE_SOURCE_MODES


def routing_context_text(markdown_text: str) -> str:
    return "\n".join(section_text(markdown_text, heading) for heading in ROUTING_HEADINGS).lower()
