#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import workflow_routing as wr
from markdown_table import MarkdownTableError, parse_markdown_tables


VALID_SOURCE_MODES = wr.RELEASE_SOURCE_MODES

ARTIFACT_KINDS = {"jar", "dist", "container", "package"}
ARTIFACT_SIGNAL_RE = re.compile(
    r"(\b(jar|dist|container)\b"
    r"|\b(docker|container)\s+image\b"
    r"|\b(deploy|deployment|release|build)\s+(package|bundle)\b"
    r"|\.jar\b"
    r"|\b(?:dist|release|deploy|deployment|build)[\w./-]*\.(?:zip|tar\.gz)\b"
    r"|部署包|发布包|构建产物|镜像)",
    re.IGNORECASE,
)
WAIVER_ALLOWED_TO_SHIP = wr.WAIVER_ALLOWED_TO_SHIP
WAIVER_ALLOWED_TO_CONTINUE = wr.WAIVER_ALLOWED_TO_CONTINUE
WAIVER_KEYWORDS = (
    "release artifact",
    "artifact source",
    "release-source",
    "release source",
    "source gate",
    "发布产物",
    "产物来源",
)

PACKET_REQUIRED_FILES = (
    "git-status-short.txt",
    "git-diff-stat.txt",
    "changed-files.txt",
    "changed-source-files.txt",
    "source-manifest.json",
    "artifact-sha256.txt",
)
SOURCE_MANIFEST_REQUIRED_FIELDS = (
    "build_command",
    "created_at",
    "artifact_sha256",
    "changed_source_files",
)
INTENDED_SOURCE_FILES = "intended-source-files.json"
INTENDED_SOURCE_SCHEMA_VERSION = "release-source-intended-files-v1"

SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}(?:\s+.+)?$")
SHA256_DIGEST_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def is_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    return (
        not normalized
        or normalized in {"待填写", "not-created", "not-needed", "none", "required"}
        or "<run_id>" in normalized
    )


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("/", "_")


def truthy_required(value: str) -> bool:
    return clean_cell(value).lower() in {"yes", "true", "required", "是"}


def accepted_risk(value: str) -> bool:
    return clean_cell(value).lower() == "accepted"


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


def remove_section(markdown_text: str, heading: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    in_section = False

    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            in_section = False
        if not in_section:
            output.append(line)
    return "\n".join(output)


def extract_table(markdown_text: str, heading: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    section_text = "\n".join(extract_section(markdown_text, heading))
    try:
        tables = parse_markdown_tables(section_text, strict=False)
    except MarkdownTableError:
        return rows
    if not tables:
        return rows

    table = tables[0]
    header = [normalize_key(cell) for cell in table.headers]
    for cells in table.rows:
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, [clean_cell(cell) for cell in cells])))
    return rows


def extract_release_gate(progress_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    section_text = "\n".join(extract_section(progress_text, "## Release Artifact Source Gate"))
    try:
        tables = parse_markdown_tables(section_text, strict=False)
    except MarkdownTableError:
        return fields
    if not tables:
        return fields

    for cells in tables[0].rows:
        if len(cells) != 2:
            continue
        key, value = [clean_cell(cell) for cell in cells]
        if key.lower() == "item" or set(key) <= {"-", " "}:
            continue
        fields[key] = value

    return fields


def extract_named_section_value(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading)).lower()


def extract_risk_tier(markdown_text: str) -> str | None:
    return wr.extract_risk_tier(markdown_text)


def strict_trigger_required(
    task_plan_text: str | None,
    release_fields: dict[str, str],
    progress_text: str | None = None,
) -> bool:
    if task_plan_text is None:
        return False

    tier = extract_risk_tier(task_plan_text)
    risk_or_impact = (
        tier == "release"
        or wr.has_external_system_scope(task_plan_text)
    )

    artifact = clean_cell(release_fields.get("Artifact", "")).lower()
    artifact_required = artifact in ARTIFACT_KINDS
    if not artifact_required:
        progress_without_gate = remove_section(progress_text or "", "## Release Artifact Source Gate")
        artifact_required = bool(
            ARTIFACT_SIGNAL_RE.search(task_plan_text)
            or (progress_without_gate and ARTIFACT_SIGNAL_RE.search(progress_without_gate))
        )
    return risk_or_impact and artifact_required


def resolve_path(root: Path, value: str) -> Path:
    value = clean_cell(value)
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def read_sha256(value: str, root: Path) -> tuple[str | None, str | None]:
    value = clean_cell(value)
    if is_placeholder(value):
        return None, "artifact sha256 is missing"

    candidate = resolve_path(root, value)
    if candidate.exists():
        try:
            first_line = candidate.read_text(encoding="utf-8").splitlines()[0].strip()
        except (OSError, IndexError):
            return None, f"artifact sha256 file is unreadable or empty: {value}"
        if SHA256_RE.match(first_line):
            return first_line, None
        return None, f"artifact sha256 file does not start with a sha256 digest: {value}"

    if SHA256_RE.match(value):
        return value, None
    return None, "artifact sha256 must be a digest or a path to artifact-sha256.txt"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_root_registry(root: Path) -> dict[str, wr.SourceRoot]:
    conventions = root / ".agents" / "references" / "project-conventions.md"
    if not conventions.is_file():
        return {}
    return wr.parse_source_root_registry(conventions.read_text(encoding="utf-8"))


def normalized_changed_source_files(values: Any) -> set[str]:
    normalized: set[str] = set()
    if not isinstance(values, list):
        return normalized
    for item in values:
        if isinstance(item, str):
            path = clean_cell(item)
            if path:
                normalized.add(path)
        elif isinstance(item, dict):
            path = clean_cell(str(item.get("path", "")))
            root_id = clean_cell(str(item.get("root_id", "")))
            if path:
                normalized.add(f"{root_id}:{path}" if root_id else path)
    return normalized


def packet_artifact_digest(packet: Path) -> str | None:
    sha_file = packet / "artifact-sha256.txt"
    if not sha_file.is_file():
        return None
    sha_text = sha_file.read_text(encoding="utf-8").strip().splitlines()
    if not sha_text:
        return None
    digest = sha_text[0].strip().split()[0]
    return digest if SHA256_DIGEST_RE.match(digest) else None


def validate_intended_source_files(
    root: Path,
    packet: Path,
    source_mode: str,
    *,
    compare_current_worktree: bool = True,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    intended_keys: set[str] = set()
    intended_path = packet / INTENDED_SOURCE_FILES
    if source_mode not in {"source-manifest-build", "allowed-diff-build"}:
        return errors, intended_keys
    if not intended_path.is_file():
        return [f"{source_mode} requires {INTENDED_SOURCE_FILES} with per-file sha256 entries"], intended_keys
    if intended_path.stat().st_size == 0:
        return [f"{INTENDED_SOURCE_FILES} is empty"], intended_keys

    try:
        payload = json.loads(intended_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{INTENDED_SOURCE_FILES} is invalid JSON: {exc.msg}"], intended_keys

    if payload.get("schema_version") != INTENDED_SOURCE_SCHEMA_VERSION:
        errors.append(f"{INTENDED_SOURCE_FILES} schema_version must be {INTENDED_SOURCE_SCHEMA_VERSION}")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        errors.append(f"{INTENDED_SOURCE_FILES} files must be a non-empty array")
        return errors, intended_keys

    registry = source_root_registry(root)

    for index, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}] must be an object")
            continue
        rel_path = clean_cell(str(item.get("path", "")))
        root_id = clean_cell(str(item.get("root_id", "")))
        digest = clean_cell(str(item.get("sha256", "")))
        reason = clean_cell(str(item.get("reason", "")))
        if is_placeholder(rel_path):
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].path is missing")
            continue
        intended_keys.add(f"{root_id}:{rel_path}" if root_id else rel_path)
        candidate = Path(rel_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].path must be repo-relative and stay inside the repo")
            continue
        if not SHA256_DIGEST_RE.match(digest):
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].sha256 must be a 64-character hex digest")
        if is_placeholder(reason):
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].reason is missing")
        if not compare_current_worktree:
            continue
        if root_id:
            source_root = registry.get(root_id)
            if source_root is None:
                errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].root_id is not declared in Source Root Registry: {root_id}")
                continue
            source_file = root / source_root.source_root / candidate
        else:
            source_file = root / candidate
        if not source_file.is_file():
            errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].path does not exist: {rel_path}")
            continue
        if SHA256_DIGEST_RE.match(digest):
            try:
                actual = file_sha256(source_file)
            except OSError as exc:
                errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].path is unreadable: {rel_path}: {exc}")
                continue
            if actual.lower() != digest.lower():
                errors.append(f"{INTENDED_SOURCE_FILES} files[{index}].sha256 does not match current file: {rel_path} (release-source drift)")
    return errors, intended_keys


def validate_packet(root: Path, packet_value: str, source_mode: str, *, historical_packet: bool = False) -> list[str]:
    errors: list[str] = []
    if is_placeholder(packet_value):
        return ["release-source packet is missing"]

    packet = resolve_path(root, packet_value)
    if not packet.is_dir():
        return [f"release-source packet directory does not exist: {packet_value}"]

    for filename in PACKET_REQUIRED_FILES:
        path = packet / filename
        if not path.is_file():
            errors.append(f"missing release-source file: {filename}")
        elif filename != "git-diff-stat.txt" and path.stat().st_size == 0:
            errors.append(f"release-source file is empty: {filename}")

    manifest = packet / "source-manifest.json"
    manifest_artifact_sha = ""
    changed_file_keys: set[str] = set()
    if manifest.is_file():
        try:
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"source-manifest.json is invalid JSON: {exc.msg}")
        else:
            if not isinstance(manifest_payload, dict):
                errors.append("source-manifest.json must be a JSON object")
            else:
                for field in SOURCE_MANIFEST_REQUIRED_FIELDS:
                    if field not in manifest_payload:
                        errors.append(f"source-manifest.json missing required field: {field}")
                build_command = clean_cell(str(manifest_payload.get("build_command", "")))
                created_at = clean_cell(str(manifest_payload.get("created_at", "")))
                artifact_sha = clean_cell(str(manifest_payload.get("artifact_sha256", "")))
                changed_files = manifest_payload.get("changed_source_files")
                manifest_artifact_sha = artifact_sha
                changed_file_keys = normalized_changed_source_files(changed_files)
                if not build_command:
                    errors.append("source-manifest.json build_command is missing")
                if not created_at:
                    errors.append("source-manifest.json created_at is missing")
                if artifact_sha and not SHA256_DIGEST_RE.match(artifact_sha):
                    errors.append("source-manifest.json artifact_sha256 must be a 64-character hex digest")
                if not isinstance(changed_files, list) or not changed_files:
                    errors.append("source-manifest.json changed_source_files must be a non-empty array")

    sha_file = packet / "artifact-sha256.txt"
    if sha_file.is_file():
        sha_text = sha_file.read_text(encoding="utf-8").strip().splitlines()
        if not sha_text or not SHA256_RE.match(sha_text[0]):
            errors.append("artifact-sha256.txt must start with a 64-character sha256 digest")
    packet_digest = packet_artifact_digest(packet)
    if manifest_artifact_sha and packet_digest and manifest_artifact_sha.lower() != packet_digest.lower():
        errors.append("source-manifest.json artifact_sha256 does not match artifact-sha256.txt")

    intended_errors, intended_keys = validate_intended_source_files(
        root,
        packet,
        source_mode,
        compare_current_worktree=not historical_packet,
    )
    errors.extend(intended_errors)
    if source_mode in {"source-manifest-build", "allowed-diff-build"} and intended_keys and changed_file_keys:
        intended_paths = {key.split(":", 1)[1] if ":" in key else key for key in intended_keys}
        changed_paths = {key.split(":", 1)[1] if ":" in key else key for key in changed_file_keys}
        extra_changed = sorted(changed_paths - intended_paths)
        missing_changed = sorted(intended_paths - changed_paths)
        if extra_changed:
            errors.append("source-manifest.json changed_source_files contains files not listed in intended-source-files.json: " + ", ".join(extra_changed))
        if missing_changed:
            errors.append("intended-source-files.json files missing from source-manifest.json changed_source_files: " + ", ".join(missing_changed))

    return errors


def waiver_complete(row: dict[str, str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    reason = row.get("reason", "")
    substitute = row.get("substitute_evidence", "")
    allowed = clean_cell(row.get("allowed_to_ship", "")).lower()
    owner = row.get("owner___follow-up", "") or row.get("owner_follow-up", "")

    if is_placeholder(reason):
        errors.append("waiver reason is missing")
    if is_placeholder(substitute):
        errors.append("waiver substitute evidence is missing")
    if allowed not in WAIVER_ALLOWED_TO_SHIP:
        errors.append("waiver allowed to ship must be yes, no, or conditional")
    elif allowed not in WAIVER_ALLOWED_TO_CONTINUE:
        errors.append("risk-accepted release source waiver cannot have allowed to ship=no")
    if is_placeholder(owner):
        errors.append("waiver owner / follow-up is missing")
    return not errors, errors


def find_release_waiver(progress_text: str) -> tuple[bool, list[str]]:
    rows = extract_table(progress_text, "## Verification Waivers")
    if not rows:
        return False, ["Verification Waivers section has no waiver rows"]

    row_errors: list[str] = []
    for row in rows:
        check = clean_cell(row.get("check", ""))
        if is_placeholder(check):
            continue
        normalized_check = check.lower()
        if not any(keyword in normalized_check for keyword in WAIVER_KEYWORDS):
            continue
        complete, errors = waiver_complete(row)
        if complete:
            return True, []
        row_errors.extend(errors)

    if row_errors:
        return False, row_errors
    return False, ["risk-accepted requires a release artifact source waiver"]


def validate(
    root: Path,
    progress_path: Path,
    task_plan_path: Path | None = None,
    strict_trigger: bool = False,
    historical_packet: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    waiver_errors: list[str] = []
    waiver_linked = False

    if not progress_path.is_file():
        return {
            "status": "fail",
            "errors": [f"progress file not found: {progress_path}"],
            "warnings": [],
            "waiver_errors": [],
            "source_mode": None,
            "release_source_packet": None,
            "validation_scope": "historical-packet" if historical_packet else "current-worktree",
            "strict_trigger_required": False,
            "waiver_linked": False,
        }

    progress_text = progress_path.read_text(encoding="utf-8")
    fields = extract_release_gate(progress_text)
    if not fields:
        return {
            "status": "fail",
            "errors": ["Release Artifact Source Gate section not found"],
            "warnings": [],
            "waiver_errors": [],
            "source_mode": None,
            "release_source_packet": None,
            "validation_scope": "historical-packet" if historical_packet else "current-worktree",
            "strict_trigger_required": False,
            "waiver_linked": False,
        }

    task_plan_text: str | None = None
    if task_plan_path is not None:
        if not task_plan_path.is_file():
            return {
                "status": "fail",
                "errors": [f"task plan file not found: {task_plan_path}"],
                "warnings": [],
                "waiver_errors": [],
                "source_mode": None,
                "release_source_packet": None,
                "validation_scope": "historical-packet" if historical_packet else "current-worktree",
                "strict_trigger_required": False,
                "waiver_linked": False,
            }
        task_plan_text = task_plan_path.read_text(encoding="utf-8")

    required = fields.get("Required", "")
    source_mode = clean_cell(fields.get("Source mode", ""))
    packet_value = fields.get("Release-source packet", "")
    artifact_sha_value = fields.get("Artifact sha256", "")
    risk_acceptance = fields.get("Explicit user risk acceptance", "")
    strict_required = strict_trigger and strict_trigger_required(task_plan_text, fields, progress_text)

    if strict_required and (not truthy_required(required) or source_mode == "not-needed"):
        errors.append("strict trigger requires Release Artifact Source Gate to be required")

    if not errors and (not truthy_required(required) or source_mode == "not-needed"):
        return {
            "status": "pass",
            "errors": [],
            "warnings": [],
            "waiver_errors": [],
            "source_mode": source_mode or "not-needed",
            "release_source_packet": clean_cell(packet_value) or "not-needed",
            "validation_scope": "historical-packet" if historical_packet else "current-worktree",
            "strict_trigger_required": strict_required,
            "waiver_linked": False,
        }

    if source_mode not in VALID_SOURCE_MODES:
        errors.append(f"invalid source mode: {source_mode or '<empty>'}")

    if source_mode == "blocked":
        errors.append("source mode is blocked")
    elif source_mode == "clean-source-build":
        _, error = read_sha256(artifact_sha_value, root)
        if error:
            errors.append(error)
        clean_evidence = (
            fields.get("Clean source evidence", "")
            or fields.get("Git status evidence", "")
            or fields.get("Source tree evidence", "")
        )
        if is_placeholder(clean_evidence):
            errors.append("clean-source-build requires Clean source evidence or Git status evidence")
    elif source_mode in {"source-manifest-build", "allowed-diff-build"}:
        errors.extend(validate_packet(root, packet_value, source_mode, historical_packet=historical_packet))
        if source_mode == "allowed-diff-build":
            packet_path = resolve_path(root, packet_value)
            allowed_scope = packet_path / "allowed-source-scope.txt"
            if allowed_scope.is_file() and allowed_scope.read_text(encoding="utf-8").strip():
                warnings.append("legacy_source_scope_used: allowed-source-scope.txt is compatibility-only; new release packets should prefer intended-source-files.json plus source-manifest.json")
            else:
                warnings.append("legacy_source_scope_not_used: allowed-diff-build validated with intended-source-files.json plus source-manifest.json")
        gate_digest, error = read_sha256(artifact_sha_value, root)
        if error:
            errors.append(error)
        packet_path = resolve_path(root, packet_value)
        packet_digest = packet_artifact_digest(packet_path) if packet_path.is_dir() else None
        if gate_digest and packet_digest and gate_digest.split()[0].lower() != packet_digest.lower():
            errors.append("Release Artifact Source Gate Artifact sha256 does not match release-source packet artifact-sha256.txt")

    if errors and accepted_risk(risk_acceptance):
        if source_mode != "blocked":
            errors.append("risk-accepted requires Source mode=blocked")
            return {
                "status": "fail",
                "errors": errors,
                "warnings": warnings,
                "waiver_errors": ["risk-accepted requires Source mode=blocked"],
                "source_mode": source_mode,
                "release_source_packet": clean_cell(packet_value),
                "validation_scope": "historical-packet" if historical_packet else "current-worktree",
                "strict_trigger_required": strict_required,
                "waiver_linked": False,
            }
        waiver_linked, waiver_errors = find_release_waiver(progress_text)
        if not waiver_linked:
            errors.extend(waiver_errors)
            return {
                "status": "fail",
                "errors": errors,
                "warnings": warnings,
                "waiver_errors": waiver_errors,
                "source_mode": source_mode,
                "release_source_packet": clean_cell(packet_value),
                "validation_scope": "historical-packet" if historical_packet else "current-worktree",
                "strict_trigger_required": strict_required,
                "waiver_linked": False,
            }
        warnings.extend(errors)
        return {
            "status": "risk-accepted",
            "errors": [],
            "warnings": warnings,
            "waiver_errors": [],
            "source_mode": source_mode,
            "release_source_packet": clean_cell(packet_value),
            "validation_scope": "historical-packet" if historical_packet else "current-worktree",
            "strict_trigger_required": strict_required,
            "waiver_linked": True,
        }

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "waiver_errors": waiver_errors,
        "source_mode": source_mode,
        "release_source_packet": clean_cell(packet_value),
        "validation_scope": "historical-packet" if historical_packet else "current-worktree",
        "strict_trigger_required": strict_required,
        "waiver_linked": waiver_linked,
    }


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"source_mode: {payload.get('source_mode') or 'none'}")
    print(f"release_source_packet: {payload.get('release_source_packet') or 'none'}")
    print(f"validation_scope: {payload.get('validation_scope') or 'current-worktree'}")
    if payload["warnings"]:
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    if payload["errors"]:
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Release Artifact Source Gate evidence.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file to inspect.")
    parser.add_argument("--task-plan", help="Optional task_plan.md path used with --strict-trigger.")
    parser.add_argument("--strict-trigger", action="store_true", help="Fail if release/external-system artifact builds are marked not-needed.")
    parser.add_argument(
        "--historical-packet",
        action="store_true",
        help="Validate packet schema and internal consistency without comparing intended source sha256 against the current worktree. Use only for archived packet audits.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path
    task_plan_path = Path(args.task_plan) if args.task_plan else None
    if task_plan_path is not None and not task_plan_path.is_absolute():
        task_plan_path = root / task_plan_path

    payload = validate(
        root,
        progress_path,
        task_plan_path=task_plan_path,
        strict_trigger=args.strict_trigger,
        historical_packet=args.historical_packet,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        emit_text(payload)
    return 0 if payload["status"] in {"pass", "risk-accepted"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
