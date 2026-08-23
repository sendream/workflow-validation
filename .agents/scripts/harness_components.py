#!/usr/bin/env python3
"""Stable identifiers for harness architecture, mechanisms, and signals."""

from __future__ import annotations

from pathlib import Path

from markdown_document import section, table_dict_rows


ARCHITECTURE_MODULE_IDS = (
    "task-spec-routing",
    "context-knowledge",
    "capability-execution",
    "lifecycle-recovery",
    "observation-evidence",
    "verification-eval",
    "governance-human",
    "evolution-experiment",
)

MECHANISM_IDS = (
    "evidence-governance",
    "release-provenance",
    "task-closeout",
    "role-reviewer",
    "dynamic-agent-campaign",
    "structural-index",
    "skill-governance",
    "archive-memory",
)

SIGNAL_CLASS_IDS = ("flow-tax",)
REPORT_IDS = MECHANISM_IDS + SIGNAL_CLASS_IDS
ATTRIBUTION_PHASES = ("baseline", "validation", "pilot", "rollback-check")
TASK_EPOCHS = ("current", "migration", "legacy")


def _ids_from_section(text: str, heading: str, key: str) -> set[str]:
    block = section(text, heading)
    return {
        str(row.get(key, "")).strip()
        for row in table_dict_rows(block, strict=True)
        if str(row.get(key, "")).strip()
    }


def validate_registry_parity(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    observed = {
        "architecture": _ids_from_section(text, "## Architecture Modules", "architecture_id"),
        "mechanism": _ids_from_section(text, "## Mechanism Registry", "component_id"),
        "signal": _ids_from_section(text, "## Signal Classes", "signal_id"),
    }
    expected = {
        "architecture": set(ARCHITECTURE_MODULE_IDS),
        "mechanism": set(MECHANISM_IDS),
        "signal": set(SIGNAL_CLASS_IDS),
    }
    errors: list[str] = []
    for category in ("architecture", "mechanism", "signal"):
        missing = sorted(expected[category] - observed[category])
        extra = sorted(observed[category] - expected[category])
        if missing:
            errors.append(f"{category} registry missing IDs: {', '.join(missing)}")
        if extra:
            errors.append(f"{category} registry has unknown IDs: {', '.join(extra)}")
    return errors
