#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from run_manifest_contract import FAIL_STATUSES, PASS_STATUSES, execution_outcome, validate_workflow_attribution


PLACEHOLDERS = {"", "待填写", "pending", "missing", "required", "unknown"}
VALID_STATUSES = {"pass", "passed", "fail", "failed", "skipped", "blocked", "waived", "not-needed"}
OBSERVABILITY_FIELDS = {
    "schema_version",
    "started_at",
    "completed_at",
    "duration_ms",
    "tool_runtime_ms",
    "blocked_reason",
    "redaction_status",
    "token_usage",
    "estimated_cost",
}
OBSERVABILITY_UNAVAILABLE = {"unknown", "unavailable", "not-needed", "not-tracked"}
SUPPORTED_SCHEMA_VERSIONS = {1, "1", "run-manifest-v1"}
SHA256_DIGEST_RE = re.compile(r"^[a-fA-F0-9]{64}$")
SENSITIVE_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)id_rsa($|\.)"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"\.dump$"),
    re.compile(r"\.har$"),
    re.compile(r"(^|[/._-])secrets?($|[/._-])", re.IGNORECASE),
    re.compile(r"(^|[/._-])credentials?($|[/._-])", re.IGNORECASE),
    re.compile(r"(^|[/._-])api[-_]?key($|[/._-])", re.IGNORECASE),
    re.compile(r"(^|[/._-])(access|refresh|auth)?[-_]?token($|[/._-])", re.IGNORECASE),
)
NEVER_SAFE_REPORT_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)id_rsa($|\.)"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"\.dump$"),
    re.compile(r"\.har$"),
    re.compile(r"(^|[/._-])(access|refresh|auth)?[-_]?token($|[/._-])", re.IGNORECASE),
)
SAFE_SCAN_REPORT_TYPES = {
    "redacted-scan-report",
    "secret-scan-report",
    "sensitive-scan-report",
    "dependency-scan-report",
    "sca-scan-report",
}
SAFE_SCAN_REPORT_SUFFIXES = {".json", ".txt", ".log"}
SAFE_SCAN_REPORT_NAME_RE = re.compile(
    r"(^|[-_.])((secret|sensitive|dependency|sca|policy)[-_.]?scan|scan[-_.]?(secret|sensitive|dependency|sca|policy))($|[-_.])",
    re.IGNORECASE,
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        text = text[1:-1]
    return text.strip()


def is_placeholder(value: Any) -> bool:
    normalized = clean(value).lower()
    return normalized in PLACEHOLDERS or "待填写" in normalized


def valid_sha256(value: Any) -> bool:
    if isinstance(value, str):
        return bool(SHA256_DIGEST_RE.fullmatch(clean(value)))
    if isinstance(value, dict):
        return bool(value) and all(bool(SHA256_DIGEST_RE.fullmatch(clean(item))) for item in value.values())
    return False


def valid_nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value >= 0


def valid_status_object(value: Any) -> bool:
    if isinstance(value, dict):
        status = clean(value.get("status")).lower()
        return bool(status) and status in OBSERVABILITY_UNAVAILABLE
    status = clean(value).lower()
    return bool(status) and status in OBSERVABILITY_UNAVAILABLE


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator reports parse failure
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "manifest root must be a JSON object"
    return payload, None


def nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def declared_run_id(payload: dict[str, Any]) -> str:
    return clean(payload.get("run_id")) or clean(nested_get(payload, "ids", "run_id"))


def manifest_run_id(payload: dict[str, Any], run_dir: Path) -> str:
    return declared_run_id(payload) or run_dir.name


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def path_values(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    for key in ("stdout_path", "stderr_path", "stdout_paths", "stderr_paths", "artifact_path", "artifacts"):
        for value in as_list(payload.get(key)):
            values.append((key, value))
    return values


def is_external_artifact(value: Any) -> bool:
    return isinstance(value, dict) and value.get("external") is True and bool(clean(value.get("reason")))


def artifact_path_text(value: Any) -> str:
    if isinstance(value, dict):
        return clean(value.get("path") or value.get("location") or value.get("uri"))
    return clean(value)


def artifact_type(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return clean(value.get("artifact_type") or value.get("type") or value.get("classification")).lower()


def safe_scan_report_path(path_text: str) -> bool:
    path = Path(path_text)
    lower_name = path.name.lower()
    if path.suffix.lower() not in SAFE_SCAN_REPORT_SUFFIXES:
        return False
    return bool(SAFE_SCAN_REPORT_NAME_RE.search(lower_name))


def safe_sensitive_report(value: Any, path_text: str) -> bool:
    lower = path_text.lower()
    if any(pattern.search(lower) for pattern in NEVER_SAFE_REPORT_PATTERNS):
        return False
    declared_type = artifact_type(value)
    if declared_type in SAFE_SCAN_REPORT_TYPES:
        return True
    return safe_scan_report_path(path_text)


def sensitive_path(path_text: str) -> bool:
    lower = path_text.lower()
    return any(pattern.search(lower) for pattern in SENSITIVE_PATTERNS)


def path_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_artifact_path(root: Path, run_dir: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    repo_relative = root / path
    if path_under(repo_relative, run_dir):
        return repo_relative
    run_relative = run_dir / path
    if path_under(run_relative, run_dir):
        return run_relative
    return repo_relative


def severity_append(errors: list[str], warnings: list[str], strict: bool, message: str) -> None:
    if strict:
        errors.append(message)
    else:
        warnings.append(message)


def validate_manifest(
    root: Path,
    manifest_path: Path,
    strict: bool,
    require_existing_artifacts: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    payload, load_error = load_json(manifest_path)
    if payload is None:
        return {
            "manifest": str(manifest_path),
            "status": "fail",
            "errors": [f"{manifest_path}: invalid JSON: {load_error}"],
            "warnings": [],
        }

    run_dir = manifest_path.parent
    errors.extend(validate_workflow_attribution(payload.get("workflow_attribution")))
    declared_id = declared_run_id(payload)
    run_id = manifest_run_id(payload, run_dir)
    if declared_id and declared_id != run_dir.name:
        severity_append(
            errors,
            warnings,
            strict,
            f"{run_id}: declared run_id must match manifest directory name {run_dir.name}",
        )
    if "schema_version" in payload and payload.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        severity_append(errors, warnings, strict, f"{run_id}: unsupported schema_version {payload.get('schema_version')!r}")
    if is_placeholder(declared_id):
        severity_append(errors, warnings, strict, f"{manifest_path}: missing run_id or ids.run_id")

    command = clean(payload.get("command") or payload.get("command_ref"))
    if is_placeholder(command):
        severity_append(errors, warnings, strict, f"{run_id}: missing command or command_ref")
    if payload.get("exit_code") is None:
        severity_append(errors, warnings, strict, f"{run_id}: missing exit_code")
    status = clean(payload.get("status")).lower()
    if is_placeholder(status):
        severity_append(errors, warnings, strict, f"{run_id}: missing status")
    elif status not in VALID_STATUSES:
        warnings.append(f"{run_id}: non-standard status {status}")
    exit_code = payload.get("exit_code")
    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
        severity_append(errors, warnings, strict, f"{run_id}: exit_code must be an integer")
    elif isinstance(exit_code, int) and status in PASS_STATUSES | FAIL_STATUSES:
        _outcome, outcome_errors = execution_outcome(payload)
        for message in outcome_errors:
            severity_append(errors, warnings, strict, f"{run_id}: {message}")
    for key in ("created_at", "summary"):
        if is_placeholder(payload.get(key)):
            severity_append(errors, warnings, strict, f"{run_id}: missing {key}")
    if "sha256" not in payload:
        severity_append(errors, warnings, strict, f"{run_id}: missing sha256")
    elif is_placeholder(payload.get("sha256")):
        severity_append(errors, warnings, strict, f"{run_id}: sha256 is placeholder")
    elif not valid_sha256(payload.get("sha256")):
        severity_append(errors, warnings, strict, f"{run_id}: sha256 must be a 64-hex digest or a non-empty map of 64-hex digests")

    missing_observability = sorted(field for field in OBSERVABILITY_FIELDS if field not in payload)
    if missing_observability:
        warnings.append(f"{run_id}: missing low-tax observability fields: {', '.join(missing_observability)}")
    for key in ("duration_ms", "tool_runtime_ms"):
        if key in payload and payload.get(key) is not None and not valid_nonnegative_number(payload.get(key)):
            warnings.append(f"{run_id}: {key} should be a non-negative number or null")
    for key in ("token_usage", "estimated_cost"):
        if key in payload and not valid_status_object(payload.get(key)):
            warnings.append(f"{run_id}: {key} should include status=unavailable/not-tracked/not-needed/unknown")
    if "redaction_status" in payload:
        redaction_status = clean(payload.get("redaction_status")).lower()
        if redaction_status not in OBSERVABILITY_UNAVAILABLE | {"redacted", "not-redacted", "not-applied"}:
            warnings.append(f"{run_id}: redaction_status is non-standard: {redaction_status}")

    has_stdout = not is_placeholder(payload.get("stdout_path")) or not is_placeholder(payload.get("stdout_summary")) or bool(payload.get("stdout_paths"))
    has_stderr = not is_placeholder(payload.get("stderr_path")) or not is_placeholder(payload.get("stderr_summary")) or bool(payload.get("stderr_paths"))
    if not has_stdout:
        severity_append(errors, warnings, strict, f"{run_id}: missing stdout_path/stdout_summary")
    if not has_stderr:
        severity_append(errors, warnings, strict, f"{run_id}: missing stderr_path/stderr_summary")

    linked_acceptance = payload.get("linked_acceptance_ids") or payload.get("acceptance_id")
    linked_scenario = payload.get("linked_scenario_ids") or payload.get("scenario_id")
    if not linked_acceptance and not linked_scenario:
        warnings.append(f"{run_id}: no acceptance_id/scenario_id linkage recorded")

    for key, raw_value in path_values(payload):
        if is_external_artifact(raw_value):
            continue
        path_text = artifact_path_text(raw_value)
        if is_placeholder(path_text) or path_text == "not-needed":
            continue
        if sensitive_path(path_text) and not safe_sensitive_report(raw_value, path_text):
            severity_append(errors, warnings, strict, f"{run_id}: {key} references sensitive/raw path {path_text}")
            continue
        candidate = resolve_artifact_path(root, run_dir, path_text)
        if not path_under(candidate, run_dir):
            severity_append(errors, warnings, strict, f"{run_id}: {key} must stay under {run_dir.relative_to(root)} or be explicit external: {path_text}")
            continue
        if require_existing_artifacts and not candidate.exists():
            severity_append(errors, warnings, strict, f"{run_id}: referenced artifact does not exist: {path_text}")

    return {
        "manifest": str(manifest_path.relative_to(root)) if path_under(manifest_path, root) else str(manifest_path),
        "run_id": run_id,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
    }


def run_dir_from_arg(root: Path, item: str) -> Path:
    path = Path(item)
    if not path.is_absolute():
        direct = root / path
        if direct.exists():
            path = direct
        else:
            path = root / ".agent-state" / "runs" / item
    if path.is_file() and path.name == "manifest.json":
        return path.parent
    return path


def run_dirs(root: Path) -> list[Path]:
    runs_root = root / ".agent-state" / "runs"
    if not runs_root.is_dir():
        return []
    return sorted(path for path in runs_root.iterdir() if path.is_dir() and not path.name.startswith("_") and not path.name.startswith("."))


def validate(
    root: Path,
    run_args: list[str],
    manifest_args: list[str],
    all_runs: bool,
    strict_current: bool,
    legacy_warn: bool,
    require_existing_artifacts: bool,
) -> dict[str, Any]:
    targets: list[Path] = []
    targets.extend(run_dir_from_arg(root, item) for item in run_args)
    targets.extend((Path(item) if Path(item).is_absolute() else root / item).parent for item in manifest_args)
    if all_runs:
        targets.extend(run_dirs(root))
    targets = sorted(set(path.resolve() for path in targets))
    if not targets:
        return {"status": "fail", "errors": ["no run target provided; use --run, --manifest, or --all-runs"], "warnings": [], "runs": []}

    explicit = bool(run_args or manifest_args)
    strict = strict_current or (explicit and not legacy_warn)
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []
    for run_dir in targets:
        manifest = run_dir / "manifest.json"
        if not manifest.is_file():
            message = f"{run_dir}: missing manifest.json"
            severity_append(errors, warnings, strict, message)
            results.append({"run_dir": str(run_dir), "status": "fail" if strict else "warn", "errors": [message] if strict else [], "warnings": [message] if not strict else []})
            continue
        result = validate_manifest(root, manifest, strict, require_existing_artifacts)
        results.append(result)
        errors.extend(result["errors"])
        warnings.extend(result["warnings"])

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "run_count": len(results),
        "strict": strict,
        "require_existing_artifacts": require_existing_artifacts,
        "runs": results,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate .agent-state run evidence manifests without release provenance semantics.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--run", action="append", default=[], help="Run id or run directory to validate. May be repeated.")
    parser.add_argument("--manifest", action="append", default=[], help="Manifest path to validate. May be repeated.")
    parser.add_argument("--all-runs", action="store_true", help="Validate all .agent-state/runs/<run_id>/ directories.")
    parser.add_argument("--strict-current", action="store_true", help="Fail missing/invalid fields for current or explicitly required runs.")
    parser.add_argument("--legacy-warn", action="store_true", help="Warn instead of failing legacy run manifest gaps.")
    artifact_group = parser.add_mutually_exclusive_group()
    artifact_group.add_argument("--require-existing-artifacts", action="store_true", help="Require referenced local artifacts to exist.")
    artifact_group.add_argument("--no-require-existing-artifacts", action="store_true", help="Do not require referenced local artifacts to exist.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"runs: {payload.get('run_count', 0)}")
    for error in payload.get("errors", []):
        print(f"error: {error}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    require_existing = bool(args.require_existing_artifacts)
    payload = validate(
        root,
        args.run,
        args.manifest,
        args.all_runs,
        args.strict_current,
        args.legacy_warn,
        require_existing,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(payload)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
