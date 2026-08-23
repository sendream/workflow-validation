#!/usr/bin/env python3
"""Mechanical claim bound: a PASS/COMPLETE command claim needs a run manifest or an explicit incomplete status.

This is M09. It is not a closeout ceremony and not a prompt slogan.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_document as md_doc
import workflow_routing as wr


MANIFEST_RE = re.compile(r"\.agent-state/runs/([A-Za-z0-9._-]+)/manifest\.json")
COMMAND_EVIDENCE_SIGNAL_RE = re.compile(
    r"(\bpytest\b|\bpython3?\b|\bbash\b|\bsh\b|\bnpm\b|\bpnpm\b|\byarn\b|\bnode\b|\bgo\s+test\b|"
    r"\bmvn\b|\bgradle\b|\bcargo\b|\bgit\s+diff\b|\bpy_compile\b|run-workflow-evals|"
    r"verify-workflow-smoke|exit\s+0|terminal output|local stdout|\bstdout\b|\bstderr\b)",
    re.IGNORECASE,
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
EXPLICIT_INCOMPLETE = {
    "FAIL",
    "FAILED",
    "BLOCKED",
    "PENDING",
    "INCOMPLETE",
    "WAIVED",
    "NOT_APPLICABLE",
    "NOT-RUN",
    "NOT_RUN",
    "NOTRUN",
    "MANUAL",
}


def clean(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean(value).lower().replace(" ", "_").replace("/", "_")


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    return md_doc.table_dict_rows(
        md_doc.section(markdown_text, heading),
        strict=False,
        normalize_key=normalize_key,
        legacy_pipe_rows=True,
    )


def has_run_manifest_reference(value: str) -> bool:
    cleaned = clean(value)
    if "manifest:" in cleaned.lower():
        ref = wr.parse_evidence_ref(cleaned)
        if ref and ref.ref_type == "manifest" and MANIFEST_RE.search(ref.target):
            return True
    return bool(MANIFEST_RE.search(cleaned))


def has_typed_non_run_reference(value: str) -> bool:
    lowered = clean(value).lower()
    return any(prefix in lowered for prefix in TYPED_NON_RUN_REF_PREFIXES)


def has_durable_run_artifact(value: str) -> bool:
    cleaned = clean(value)
    return ".agents/runs/" in cleaned or bool(MANIFEST_RE.search(cleaned))


def command_pass_rows(progress_text: str) -> list[dict[str, str]]:
    errors: list[str] = []
    checked_rows = 0
    for row in extract_table(progress_text, "## Final Evidence Ledger"):
        acceptance_id = clean(row.get("acceptance_id", "<unknown>"))
        if acceptance_id.lower() in {"", "not-needed", "待填写"}:
            continue
        final_status = clean(row.get("final_status", "")).upper()
        if final_status in EXPLICIT_INCOMPLETE:
            continue
        if final_status != "PASS":
            continue
        combined = " ".join(clean(row.get(key, "")) for key in ("supplemental_evidence", "artifact", "notes"))
        if not COMMAND_EVIDENCE_SIGNAL_RE.search(combined):
            continue
        checked_rows += 1
        if not has_run_manifest_reference(combined) and not has_durable_run_artifact(combined):
            errors.append(
                f"ledger {acceptance_id}: command/terminal PASS evidence must reference "
                ".agent-state/runs/<run_id>/manifest.json or durable run artifact"
            )
        elif has_typed_non_run_reference(combined) and not has_run_manifest_reference(combined):
            errors.append(
                f"ledger {acceptance_id}: command PASS cannot rely only on commit/source/artifact typed refs; "
                "add .agent-state/runs/<run_id>/manifest.json"
            )
    for row in extract_table(progress_text, "## Validation"):
        command = clean(row.get("command", ""))
        result = clean(row.get("result", "") or row.get("status", "")).lower()
        artifact = clean(row.get("artifact", "") or row.get("evidence", ""))
        if not command or not COMMAND_EVIDENCE_SIGNAL_RE.search(command):
            continue
        if result not in {"pass", "passed", "0", "ok", "success"}:
            continue
        checked_rows += 1
        combined = f"{artifact} {command}"
        if not has_run_manifest_reference(combined) and not has_durable_run_artifact(combined):
            errors.append(
                f"Validation command `{command}` passed without "
                ".agent-state/runs/<run_id>/manifest.json or durable run artifact"
            )
    for row in extract_table(progress_text, "## Acceptance Evidence"):
        acceptance_id = clean(row.get("acceptance_id", "<unknown>"))
        if acceptance_id.lower() in {"", "not-needed", "待填写"}:
            continue
        status = clean(row.get("status", "") or row.get("final_status", "")).upper()
        if status in EXPLICIT_INCOMPLETE:
            continue
        if status not in {"PASS", "PASSED"}:
            continue
        combined = " ".join(
            clean(row.get(key, "")) for key in ("evidence", "evidence_location", "notes", "artifact")
        )
        if not COMMAND_EVIDENCE_SIGNAL_RE.search(combined):
            continue
        checked_rows += 1
        if not has_run_manifest_reference(combined) and not has_durable_run_artifact(combined):
            errors.append(
                f"Acceptance Evidence {acceptance_id}: command/terminal PASS must reference "
                ".agent-state/runs/<run_id>/manifest.json or durable run artifact"
            )
        elif has_typed_non_run_reference(combined) and not has_run_manifest_reference(combined):
            errors.append(
                f"Acceptance Evidence {acceptance_id}: command PASS cannot rely only on "
                "commit/source/artifact typed refs; add .agent-state/runs/<run_id>/manifest.json"
            )
    return {"status": "pass" if not errors else "fail", "checked_rows": checked_rows, "errors": errors}


def validate(progress_text: str) -> dict[str, Any]:
    check = command_pass_rows(progress_text)
    return {
        "status": check["status"],
        "errors": list(check["errors"]),
        "warnings": [],
        "checks": {"command_pass_evidence_manifest": check},
        "strict_required": False,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail a PASS/COMPLETE command claim that is not bound to a run manifest or explicit incomplete status."
    )
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def emit_text(payload: dict[str, Any]) -> None:
    print(payload["status"])
    for error in payload.get("errors", []):
        print(f"error: {error}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path
    if not progress_path.is_file():
        payload = {"status": "fail", "errors": [f"progress not found: {progress_path}"], "warnings": [], "checks": {}}
    else:
        payload = validate(progress_path.read_text(encoding="utf-8"))
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
