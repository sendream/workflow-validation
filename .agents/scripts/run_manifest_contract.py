#!/usr/bin/env python3
"""Optional workflow attribution contract for derived run manifests."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

from harness_components import ATTRIBUTION_PHASES, MECHANISM_IDS, TASK_EPOCHS


CANDIDATE_ID_RE = re.compile(r"^HC-[A-Za-z0-9][A-Za-z0-9._-]*$")
ATTRIBUTION_FIELDS = ("candidate_id", "component_id", "phase", "task_epoch")
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
PASS_STATUSES = {"pass", "passed", "success", "ok"}
FAIL_STATUSES = {"fail", "failed", "blocked", "error"}
OUTCOME_PHASES = {"validation", "pilot", "rollback-check"}


def clean(value: Any) -> str:
    return str(value or "").strip()


def validate_workflow_attribution(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return ["workflow_attribution must be an object"]

    errors: list[str] = []
    missing = [field for field in ATTRIBUTION_FIELDS if not clean(value.get(field))]
    if missing:
        errors.append("workflow_attribution missing required fields: " + ", ".join(missing))

    candidate_id = clean(value.get("candidate_id"))
    component_id = clean(value.get("component_id")).lower()
    phase = clean(value.get("phase")).lower()
    task_epoch = clean(value.get("task_epoch")).lower()
    candidate_sha256 = clean(value.get("candidate_sha256")).lower()
    candidate_ref = clean(value.get("candidate_ref"))
    candidate_result_sha256 = clean(value.get("candidate_result_sha256")).lower()
    candidate_result_ref = clean(value.get("candidate_result_ref"))
    if candidate_id and not CANDIDATE_ID_RE.fullmatch(candidate_id):
        errors.append(f"workflow_attribution invalid candidate_id: {candidate_id}")
    if component_id and component_id not in MECHANISM_IDS:
        errors.append(f"workflow_attribution unknown component_id: {component_id}")
    if phase and phase not in ATTRIBUTION_PHASES:
        errors.append(f"workflow_attribution invalid phase: {phase}")
    if task_epoch and task_epoch not in TASK_EPOCHS:
        errors.append(f"workflow_attribution invalid task_epoch: {task_epoch}")
    if candidate_sha256 and not SHA256_RE.fullmatch(candidate_sha256):
        errors.append("workflow_attribution candidate_sha256 must be a 64-hex digest")
    if candidate_ref:
        candidate_path = Path(candidate_ref)
        if candidate_path.is_absolute() or ".." in candidate_path.parts:
            errors.append("workflow_attribution candidate_ref must be a safe project-relative path")
    if candidate_result_sha256 and not SHA256_RE.fullmatch(candidate_result_sha256):
        errors.append("workflow_attribution candidate_result_sha256 must be a 64-hex digest")
    if candidate_result_ref:
        result_path = Path(candidate_result_ref)
        if result_path.is_absolute() or ".." in result_path.parts:
            errors.append("workflow_attribution candidate_result_ref must be a safe project-relative path")
    return errors


def workflow_attribution(payload: dict[str, Any]) -> dict[str, str] | None:
    value = payload.get("workflow_attribution")
    if value is None or validate_workflow_attribution(value):
        return None
    assert isinstance(value, dict)
    result = {field: clean(value.get(field)).lower() if field != "candidate_id" else clean(value.get(field)) for field in ATTRIBUTION_FIELDS}
    if clean(value.get("candidate_sha256")):
        result["candidate_sha256"] = clean(value.get("candidate_sha256")).lower()
    if clean(value.get("candidate_ref")):
        result["candidate_ref"] = clean(value.get("candidate_ref"))
    if clean(value.get("candidate_result_sha256")):
        result["candidate_result_sha256"] = clean(value.get("candidate_result_sha256")).lower()
    if clean(value.get("candidate_result_ref")):
        result["candidate_result_ref"] = clean(value.get("candidate_result_ref"))
    return result


def execution_outcome(payload: dict[str, Any]) -> tuple[str, list[str]]:
    status = clean(payload.get("status")).lower()
    exit_code = payload.get("exit_code")
    errors: list[str] = []
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return "invalid", ["exit_code must be an integer, not a boolean or non-integer"]
    if status in PASS_STATUSES:
        if exit_code != 0:
            errors.append(f"status={status} requires exit_code=0")
        return ("pass" if not errors else "invalid"), errors
    if status in FAIL_STATUSES:
        if exit_code == 0:
            errors.append(f"status={status} requires non-zero exit_code")
        return ("fail" if not errors else "invalid"), errors
    return "invalid", [f"status must be an explicit pass/fail terminal status, not {status or '<empty>'}"]


def _safe_regular_file_under(parent: Path, relative_text: str) -> Path | None:
    relative = Path(relative_text)
    if not relative_text or relative.is_absolute() or ".." in relative.parts:
        return None
    current = parent
    for index, part in enumerate(relative.parts):
        current /= part
        try:
            mode = current.lstat().st_mode
        except OSError:
            return None
        if stat.S_ISLNK(mode):
            return None
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(mode):
            return None
    return current if relative.parts and stat.S_ISREG(mode) else None


def validate_stream_artifacts(manifest_path: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sha256 = payload.get("sha256") if isinstance(payload.get("sha256"), dict) else {}
    for stream in ("stdout", "stderr"):
        path_key = f"{stream}_path"
        relative = clean(payload.get(path_key))
        artifact = _safe_regular_file_under(manifest_path.parent, relative)
        if artifact is None:
            errors.append(f"{path_key} must reference an existing safe regular file under the run directory")
            continue
        expected = clean(sha256.get(stream)).lower()
        if not SHA256_RE.fullmatch(expected):
            errors.append(f"sha256.{stream} must be a 64-hex digest")
            continue
        actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"sha256.{stream} does not match {path_key}")
    return errors


def candidate_file_sha256(root: Path, reference: str) -> tuple[str | None, str | None]:
    artifact = _safe_regular_file_under(root, clean(reference))
    if artifact is None:
        return None, "candidate_ref must reference an existing safe regular file under the project root"
    return hashlib.sha256(artifact.read_bytes()).hexdigest(), None


def validate_candidate_result_artifact(manifest_path: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    attribution = workflow_attribution(payload)
    if attribution is None:
        return ["candidate result requires valid workflow_attribution"]
    result_ref = clean(attribution.get("candidate_result_ref"))
    result_sha256 = clean(attribution.get("candidate_result_sha256")).lower()
    if not result_ref or not result_sha256:
        return ["outcome attribution requires candidate_result_ref and candidate_result_sha256"]
    try:
        project_root = manifest_path.resolve().parents[3]
    except IndexError:
        return ["outcome manifest path cannot establish project root for candidate result"]
    artifact = _safe_regular_file_under(project_root, result_ref)
    if artifact is None:
        return ["candidate_result_ref must reference an existing safe regular file under the project root"]
    try:
        artifact.resolve().relative_to(manifest_path.parent.resolve())
    except ValueError:
        errors.append("candidate_result_ref must stay under its run directory")
    actual_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if actual_sha256 != result_sha256:
        errors.append("candidate_result_sha256 does not match candidate_result_ref")
    try:
        result = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"candidate_result_ref must contain valid JSON: {exc}")
        return errors
    if not isinstance(result, dict):
        return errors + ["candidate result must be a JSON object"]
    expected = {
        "schema_version": 1,
        "type": "workflow-candidate-evaluation",
        "candidate_id": attribution["candidate_id"],
        "candidate_ref": clean(attribution.get("candidate_ref")),
        "candidate_sha256": clean(attribution.get("candidate_sha256")).lower(),
        "phase": attribution["phase"],
        "status": clean(payload.get("status")).lower(),
        "exit_code": payload.get("exit_code"),
    }
    for key, value in expected.items():
        actual = result.get(key)
        if key in {"candidate_sha256", "status", "phase"}:
            actual = clean(actual).lower()
        elif key in {"candidate_id", "candidate_ref", "type"}:
            actual = clean(actual)
        if actual != value:
            errors.append(f"candidate result {key} mismatch: expected {value!r}, got {actual!r}")
    if result.get("evaluated") is not True:
        errors.append("candidate result evaluated must be true")
    return errors


def validate_outcome_manifest(
    payload: dict[str, Any],
    *,
    component_id: str,
    task_epoch: str,
    candidate_id: str | None = None,
    manifest_path: Path | None = None,
) -> list[str]:
    errors = validate_workflow_attribution(payload.get("workflow_attribution"))
    attribution = workflow_attribution(payload)
    if attribution is None:
        if not errors:
            errors.append("workflow_attribution is required for outcome evidence")
        return errors

    if payload.get("schema_version") not in {1, "1", "run-manifest-v1"}:
        errors.append("outcome manifest requires supported schema_version")
    outcome, outcome_errors = execution_outcome(payload)
    errors.extend(outcome_errors)
    if outcome != "pass":
        errors.append("outcome manifest must record status=pass and exit_code=0")
    if not clean(payload.get("run_id")):
        errors.append("outcome manifest requires run_id")
    sha256 = payload.get("sha256")
    if not isinstance(sha256, dict) or not sha256:
        errors.append("outcome manifest requires non-empty sha256 evidence")
    if manifest_path is not None:
        errors.extend(validate_stream_artifacts(manifest_path, payload))
    if attribution["component_id"] != component_id:
        errors.append(
            f"outcome attribution component mismatch: expected {component_id}, got {attribution['component_id']}"
        )
    if attribution["task_epoch"] != task_epoch:
        errors.append(
            f"outcome attribution task_epoch mismatch: expected {task_epoch}, got {attribution['task_epoch']}"
        )
    if not candidate_id:
        errors.append("outcome evidence row requires candidate_id")
    elif attribution["candidate_id"] != candidate_id:
        errors.append(
            f"outcome attribution candidate mismatch: expected {candidate_id}, got {attribution['candidate_id']}"
        )
    if attribution["phase"] not in OUTCOME_PHASES:
        errors.append("outcome attribution phase must be validation, pilot, or rollback-check")
    candidate_ref = clean(attribution.get("candidate_ref"))
    candidate_sha256 = clean(attribution.get("candidate_sha256")).lower()
    if not candidate_ref or not candidate_sha256:
        errors.append("outcome attribution requires candidate_ref and candidate_sha256")
    elif manifest_path is not None:
        try:
            project_root = manifest_path.resolve().parents[3]
        except IndexError:
            errors.append("outcome manifest path cannot establish project root")
        else:
            actual_candidate_sha256, digest_error = candidate_file_sha256(project_root, candidate_ref)
            if digest_error or actual_candidate_sha256 is None:
                errors.append(digest_error or "outcome candidate_ref digest unavailable")
            elif actual_candidate_sha256 != candidate_sha256:
                errors.append("outcome candidate_sha256 does not match candidate_ref")
        command_argv = payload.get("command_argv")
        candidate_result_ref = clean(attribution.get("candidate_result_ref"))
        if not isinstance(command_argv, list) or not all(isinstance(item, str) for item in command_argv):
            errors.append("outcome manifest requires command_argv")
        else:
            if candidate_ref not in command_argv:
                errors.append("outcome command_argv must receive candidate_ref as an exact argv token")
            if not candidate_result_ref or candidate_result_ref not in command_argv:
                errors.append("outcome command_argv must receive candidate_result_ref as an exact argv token")
        errors.extend(validate_candidate_result_artifact(manifest_path, payload))
    return errors
