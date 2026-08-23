#!/usr/bin/env python3
"""Read-only, bounded extraction of the three current-task root documents.

This module deliberately does not create files or normalize conflicting state.
Consumers can use the returned fields when available, but must respect
``source_status`` before treating a snapshot as a complete task record.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import workflow_routing as wr


STATE_FILENAMES = ("task_plan.md", "progress.md", "findings.md")
PLACEHOLDER_VALUES = {"", "none", "not-needed", "optional", "待填写", "未填写"}
PLACEHOLDER_MARKERS = ("待填写", "optional /", "todo", "tbd", "pending", "missing", "required")
ACTIVE_TASK_PATTERNS = (
    re.compile(
        r"(?:Active task id|Current task|Current active task)\s*[:：]\s*`?([^`\n]+?)`?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"(?:当前 active task|当前任务)\s*[:：]\s*`?([^`\n]+?)`?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
)
LIFECYCLE_PATTERNS = (
    re.compile(r"^\s*[-*]\s*Lifecycle state\s*[:：]\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*[-*]\s*生命周期状态\s*[:：]\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE | re.MULTILINE),
)
NEXT_ACTION_PATTERNS = (
    re.compile(r"^\s*[-*]\s*Next Action\s*[:：]\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*[-*]\s*下一步\s*[:：]\s*`?([^`\n]+?)`?\s*$", re.MULTILINE),
)


@dataclass(frozen=True)
class CurrentTaskSnapshot:
    task_id: str | None
    lifecycle_state: str | None
    risk_tier: str | None
    impact_scope: str | None
    next_action: str | None
    source_status: Literal["complete", "partial", "missing", "invalid"]
    source_digests: dict[str, str]


@dataclass(frozen=True)
class CurrentTaskRead:
    """One bounded in-memory read shared by snapshot consumers.

    The root documents remain the only durable state source.  ``source_texts``
    is an ephemeral, bounded view for one process so consumers such as the
    planning hook do not re-open the same files after creating a snapshot.
    """

    snapshot: CurrentTaskSnapshot
    source_texts: dict[str, str]
    state_bytes_read: int


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().strip("`").strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in PLACEHOLDER_VALUES or any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return None
    return cleaned


def _without_fenced_blocks(markdown_text: str) -> str:
    """Ignore examples in fenced code blocks when extracting live state."""
    lines: list[str] = []
    fence: str | None = None
    for line in markdown_text.splitlines(keepends=True):
        marker = line.lstrip()
        if marker.startswith("```") or marker.startswith("~~~"):
            token = marker[:3]
            if fence is None:
                fence = token
            elif token == fence:
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "".join(lines)


def _section_text(markdown_text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)", re.MULTILINE)
    match = pattern.search(markdown_text)
    return match.group(1) if match else ""


def extract_active_task_id(markdown_text: str, source_name: str) -> str | None:
    """Extract one non-placeholder task id using the shared snapshot grammar."""
    text = _without_fenced_blocks(markdown_text)
    for pattern in ACTIVE_TASK_PATTERNS:
        match = pattern.search(text)
        if match:
            value = _clean(match.group(1))
            if value:
                return value

    active_section = _section_text(text, "Active Task")
    if active_section:
        match = re.search(r"^\s*[-*]\s*`([^`]+)`", active_section, flags=re.MULTILINE)
        if match:
            value = _clean(match.group(1))
            if value:
                return value

    if Path(source_name).stem.lower() == "findings":
        reboot_section = _section_text(text, "Reboot Facts")
        match = re.search(r"active task[：:]\s*`([^`]+)`|当前 active task[：:]\s*`([^`]+)`", reboot_section, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1) or match.group(2))
    return None


def _first_value(markdown_text: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    text = _without_fenced_blocks(markdown_text)
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = _clean(match.group(1))
            if value:
                return value
    return None


def _read_bounded(path: Path, max_bytes: int) -> tuple[str | None, str | None, bool, bool, int]:
    """Return text, digest, truncated and invalid flags without writing state."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except FileNotFoundError:
        return None, None, False, False, 0
    except OSError:
        return None, None, False, True, 0

    truncated = len(raw) > max_bytes
    content = raw[:max_bytes]
    digest = hashlib.sha256(content).hexdigest()
    try:
        return content.decode("utf-8"), digest, truncated, False, len(raw)
    except UnicodeDecodeError:
        return None, digest, truncated, True, len(raw)


def _route_value(value: str | None, valid_values: set[str] | frozenset[str]) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized if normalized in valid_values else None


def load_current_task_read(root: Path, *, max_bytes: int = 36_000) -> CurrentTaskRead:
    """Load one bounded, in-memory view of root task state without writing.

    ``partial`` is intentional: it covers absent individual sources, byte-limit
    truncation, placeholder task ids, and contradictory non-placeholder ids.
    ``missing`` means none of the three state sources could be read; ``invalid``
    means a present source could not be decoded or read safely.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")

    root = Path(root)
    texts: dict[str, str] = {}
    digests: dict[str, str] = {}
    missing: list[str] = []
    truncated = False
    invalid = False
    state_bytes_read = 0

    for name in STATE_FILENAMES:
        text, digest, was_truncated, was_invalid, bytes_read = _read_bounded(root / name, max_bytes)
        state_bytes_read += bytes_read
        if digest is not None:
            digests[name] = digest
        if text is None:
            if was_invalid:
                invalid = True
            else:
                missing.append(name)
            continue
        texts[name] = text
        truncated = truncated or was_truncated

    task_ids_by_source = {
        name: extract_active_task_id(text, name)
        for name, text in texts.items()
    }
    task_ids = {value for value in task_ids_by_source.values() if value is not None}
    task_id = next(iter(task_ids)) if len(task_ids) == 1 else None
    task_plan = texts.get("task_plan.md", "")
    progress = texts.get("progress.md", "")
    risk_tier = _route_value(wr.extract_risk_tier(task_plan), wr.VALID_RISK_TIERS) if task_plan else None
    impact_scope = _route_value(wr.extract_impact_scope(task_plan), wr.VALID_IMPACT_SCOPES) if task_plan else None

    if invalid:
        source_status: Literal["complete", "partial", "missing", "invalid"] = "invalid"
    elif not texts:
        source_status = "missing"
    elif missing or truncated or len(task_ids) > 1 or any(value is None for value in task_ids_by_source.values()):
        source_status = "partial"
    else:
        source_status = "complete"

    snapshot = CurrentTaskSnapshot(
        task_id=task_id,
        lifecycle_state=_first_value(progress, LIFECYCLE_PATTERNS),
        risk_tier=risk_tier,
        impact_scope=impact_scope,
        next_action=_first_value(progress, NEXT_ACTION_PATTERNS),
        source_status=source_status,
        source_digests=digests,
    )
    return CurrentTaskRead(
        snapshot=snapshot,
        source_texts=texts,
        state_bytes_read=state_bytes_read,
    )


def load_current_task_snapshot(root: Path, *, max_bytes: int = 36_000) -> CurrentTaskSnapshot:
    """Load bounded task facts without creating files or retaining state."""

    return load_current_task_read(root, max_bytes=max_bytes).snapshot
