#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import markdown_table as md
import workflow_routing as wr


FINAL_STATUSES = wr.FINAL_EVIDENCE_STATUSES
WAIVER_ALLOWED_TO_SHIP = wr.WAIVER_ALLOWED_TO_SHIP
WEAK_EVIDENCE_VALUES = {
    "command",
    "test",
    "tests",
    "passed",
    "pass",
    "ok",
    "yes",
    "done",
    "terminal output",
    "not-persisted terminal output",
    "已测试",
    "看起来正常",
}
REPLAYABLE_EVIDENCE_MARKERS = (
    ".agent-state/",
    ".agents/runs/",
    "artifact:",
    "manifest:",
    "screenshot:",
    "trace:",
    "stdout:",
    "stderr:",
    "api response:",
    "api-response:",
    "manual note:",
    "manual:",
    "report:",
    "log:",
    "sha256:",
)
EVIDENCE_FILE_RE = re.compile(
    r"^(?:\.agent-state/|\.agents/runs/|\.agents/|\./|\.\./|/|[A-Za-z0-9_.-]+/)[^\s|]+"
    r"\.(?:txt|log|json|xml|html|md|png|jpg|jpeg|webp|har|trace|zip|tar\.gz)$",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}(?:\s+.+)?$")
LOCAL_EVIDENCE_PATH_RE = re.compile(
    r"(?P<path>(?:\.agent-state/|\.agents/runs/|\.agents/|\./|\.\./|/)[^\s|]+"
    r"|[A-Za-z0-9_.-]+/[^\s|]+\.(?:txt|log|json|xml|html|md|png|jpg|jpeg|webp|har|trace|zip|tar\.gz))",
    re.IGNORECASE,
)
COMMAND_PREFIX_RE = re.compile(
    r"^\s*(?:pytest|python|python3|bash|sh|npm|pnpm|yarn|node|go\s+test|mvn|gradle|cargo|curl|git)\b",
    re.IGNORECASE,
)
COMMAND_EVIDENCE_SIGNAL_RE = re.compile(
    r"(\bpytest\b|\bpython3?\b|\bbash\b|\bsh\b|\bnpm\b|\bpnpm\b|\byarn\b|\bnode\b|\bgo\s+test\b|"
    r"\bmvn\b|\bgradle\b|\bcargo\b|\bgit\s+diff\b|\bpy_compile\b|run-workflow-evals|"
    r"verify-workflow-smoke|exit\s+0|terminal output|local stdout|\bstdout\b|\bstderr\b|"
    r"\btests?\s+(?:passed|pass|green)\b|\blint\s+(?:passed|pass|green)\b|"
    r"\btype\s*check\s+(?:passed|pass|green)\b|\btypecheck\s+(?:passed|pass|green)\b|"
    r"\bbuild\s+(?:passed|pass|green)\b|\bsmoke\s+(?:passed|pass|green)\b|"
    r"\bevals?\s+(?:passed|pass|green)\b|\bchecks?\s+(?:passed|pass|green)\b)",
    re.IGNORECASE,
)
ENGLISH_REPEAT_WAIVER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:repeat|repeated|again|recurring|second time|third time)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
NUMERIC_REPEAT_WAIVER_RE = re.compile(r">=\s*2(?![A-Za-z0-9])")
CJK_REPEAT_WAIVER_TERMS = (
    "重复",
    "反复",
    "再次",
    "第二次",
    "第 2 次",
    "第三次",
    "第 3 次",
    "连续",
)


def has_repeated_waiver_signal(value: str) -> bool:
    normalized = value.lower()
    return (
        bool(ENGLISH_REPEAT_WAIVER_RE.search(normalized))
        or bool(NUMERIC_REPEAT_WAIVER_RE.search(normalized))
        or any(term in normalized for term in CJK_REPEAT_WAIVER_TERMS)
    )


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("/", "_")


def is_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    return (
        not normalized
        or normalized in {"待填写", "none", "not-needed", "missing", "pending", "required"}
        or "<run_id>" in normalized
    )


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def normalize_waiver_class(value: str) -> str:
    normalized = clean_cell(value).lower()
    if "testclient" in normalized or "fastapi" in normalized:
        return "fastapi-testclient"
    if "browser" in normalized or "playwright" in normalized or "screenshot" in normalized:
        return "browser-smoke"
    if "secret" in normalized:
        return "secret-scan"
    if "depend" in normalized or "sca" in normalized:
        return "dependency-scan"
    if "sast" in normalized or "static analysis" in normalized:
        return "sast"
    tokens = [token for token in re.split(r"[^a-z0-9_.-]+", normalized) if token]
    return " ".join(tokens[:4])


def semantic_waiver_class(row: dict[str, str]) -> str:
    check = clean_cell(row.get("check", ""))
    combined = "\n".join(
        clean_cell(row.get(field, ""))
        for field in ("check", "reason", "substitute_evidence", "owner___follow-up", "owner_follow-up")
    )
    combined_key = normalize_waiver_class(combined)
    check_key = normalize_waiver_class(check)
    if combined_key and not re.fullmatch(r"[ars]?\d+(?: [ars]?\d+)*", combined_key):
        return combined_key
    return check_key


def repeated_waiver_classes(waiver_rows: list[dict[str, str]]) -> set[str]:
    counts: dict[str, int] = {}
    classes: set[str] = set()
    for row in waiver_rows:
        combined = "\n".join(str(value) for value in row.values()).lower()
        key = semantic_waiver_class(row)
        if key:
            counts[key] = counts.get(key, 0) + 1
        if has_repeated_waiver_signal(combined):
            classes.add(key or normalize_waiver_class(combined))
    for key, count in counts.items():
        if count >= 2:
            classes.add(key)
    return {item for item in classes if item}


def repeated_waiver_signals(waiver_rows: list[dict[str, str]]) -> list[str]:
    counts: dict[str, int] = {}
    signals: list[str] = []
    for row in waiver_rows:
        check = clean_cell(row.get("check", ""))
        combined = "\n".join(str(value) for value in row.values()).lower()
        key = semantic_waiver_class(row)
        if key:
            counts[key] = counts.get(key, 0) + 1
        if has_repeated_waiver_signal(combined):
            signals.append(check or "<unknown waiver>")
    for key, count in counts.items():
        if count >= 2:
            signals.append(f"{key} x{count}")
    return sorted(set(signals))


def parse_repeat_count(value: str) -> int | None:
    match = re.search(r"\d+", clean_cell(value))
    return int(match.group(0)) if match else None


def tooling_gap_debt_missing_repeated_classes(rows: list[dict[str, str]], required_classes: set[str]) -> list[str]:
    covered: set[str] = set()
    for row in rows:
        tool_class = clean_cell(row.get("tool_class", "") or row.get("tool", ""))
        gap = clean_cell(row.get("gap", ""))
        repeat_count = parse_repeat_count(row.get("repeat_count", "") or row.get("repeat", ""))
        if is_placeholder(tool_class) and is_placeholder(gap):
            continue
        if repeat_count is None or repeat_count < 2:
            continue
        row_classes = {
            normalize_waiver_class(tool_class),
            normalize_waiver_class(gap),
            normalize_waiver_class(f"{tool_class}\n{gap}"),
        }
        for required in required_classes:
            if required in row_classes:
                covered.add(required)
    return sorted(required_classes - covered)


def looks_like_command(value: str) -> bool:
    return bool(COMMAND_PREFIX_RE.search(clean_cell(value)))


def manual_note_with_command_signal(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if not (normalized.startswith("manual note:") or normalized.startswith("manual:")):
        return False
    return bool(COMMAND_EVIDENCE_SIGNAL_RE.search(normalized))


def local_evidence_paths(value: str) -> list[str]:
    if looks_like_command(value) and not any(marker in clean_cell(value).lower() for marker in REPLAYABLE_EVIDENCE_MARKERS):
        return []
    paths: list[str] = []
    for match in LOCAL_EVIDENCE_PATH_RE.finditer(clean_cell(value)):
        path = match.group("path").strip("`").rstrip(".,;:)\"'`")
        if path:
            paths.append(path)
    return paths


def evidence_path_errors(root: Path, value: str, field_name: str) -> list[str]:
    errors: list[str] = []
    normalized = clean_cell(value).lower()
    if normalized.startswith("manual note:") or normalized.startswith("manual:"):
        return errors
    for path_value in local_evidence_paths(value):
        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError:
            # Absolute paths outside the repo are allowed as external evidence
            # references, but cannot be replay-checked by this validator.
            continue
        if not candidate.exists():
            errors.append(f"{field_name}: local evidence path does not exist: {path_value}")
    return errors


def has_replayable_pass_evidence(supplemental: str, artifact: str) -> bool:
    def evidence_like(value: str) -> bool:
        normalized = clean_cell(value).lower()
        if is_placeholder(normalized) or normalized in WEAK_EVIDENCE_VALUES:
            return False
        if manual_note_with_command_signal(value):
            return False
        if looks_like_command(value) and not any(marker in normalized for marker in REPLAYABLE_EVIDENCE_MARKERS):
            return False
        return (
            any(marker in normalized for marker in REPLAYABLE_EVIDENCE_MARKERS)
            or bool(local_evidence_paths(value))
            or bool(EVIDENCE_FILE_RE.fullmatch(clean_cell(value)))
            or bool(SHA256_RE.match(clean_cell(value)))
        )

    if evidence_like(artifact):
        return True
    return evidence_like(supplemental)


def token_set(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.split(r"[^A-Za-z0-9_.:-]+", clean_cell(value))
        if token
    }


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
    section = extract_section(markdown_text, heading)
    rows: list[dict[str, str]] = []

    for table in md.parse_markdown_tables("\n".join(section), strict=False):
        header = [normalize_key(cell) for cell in table.headers]
        for cells in table.rows:
            if len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))
    return rows


def real_rows(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    return [row for row in rows if not is_placeholder(row.get(key, ""))]


def waiver_complete(row: dict[str, str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    reason = row.get("reason", "")
    substitute = row.get("substitute_evidence", "")
    allowed = clean_cell(row.get("allowed_to_ship", "")).lower()
    owner = row.get("owner___follow-up", "") or row.get("owner_follow-up", "")

    check = row.get("check", "<unknown waiver>")
    if is_placeholder(reason):
        errors.append(f"waiver {check}: reason is missing")
    if is_placeholder(substitute):
        errors.append(f"waiver {check}: substitute evidence is missing")
    if allowed not in WAIVER_ALLOWED_TO_SHIP:
        errors.append(f"waiver {check}: allowed to ship must be yes, no, or conditional")
    if is_placeholder(owner):
        errors.append(f"waiver {check}: owner / follow-up is missing")
    return not errors, errors


def extract_named_section_value(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading)).lower()


def extract_risk_tier(markdown_text: str) -> str | None:
    return wr.extract_risk_tier(markdown_text)


def strict_trigger_required(task_plan_text: str | None) -> bool:
    if task_plan_text is None:
        return False
    tier = extract_risk_tier(task_plan_text)
    external_system = wr.has_external_system_scope(task_plan_text)
    if tier is not None:
        return tier in {"high", "release"} or external_system
    return external_system


def find_matching_waiver(
    waivers: list[dict[str, str]],
    acceptance_id: str,
    allow_single_waiver_fallback: bool = False,
) -> dict[str, str] | None:
    normalized_acceptance = clean_cell(acceptance_id).lower()
    for waiver in waivers:
        check = clean_cell(waiver.get("check", "")).lower()
        if check == normalized_acceptance or normalized_acceptance in token_set(check):
            return waiver
    if allow_single_waiver_fallback and len(waivers) == 1:
        return waivers[0]
    return None


def validate(
    progress_path: Path,
    task_plan_path: Path | None = None,
    strict_trigger: bool = False,
    allow_single_waiver_fallback: bool = False,
    require_existing_artifacts: bool = False,
    check_template: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if is_template_path(progress_path) and not check_template:
        if not progress_path.is_file():
            return {"status": "fail", "errors": [f"progress file not found: {progress_path}"], "warnings": []}
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "ledger_rows": 0,
            "waiver_rows": 0,
            "strict_trigger_required": False,
            "single_waiver_fallback_allowed": allow_single_waiver_fallback,
            "require_existing_artifacts": require_existing_artifacts,
        }
    if task_plan_path is not None and is_template_path(task_plan_path) and not check_template:
        if not task_plan_path.is_file():
            return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": []}
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "ledger_rows": 0,
            "waiver_rows": 0,
            "strict_trigger_required": False,
            "single_waiver_fallback_allowed": allow_single_waiver_fallback,
            "require_existing_artifacts": require_existing_artifacts,
        }

    if not progress_path.is_file():
        return {
            "status": "fail",
            "errors": [f"progress file not found: {progress_path}"],
            "warnings": [],
            "ledger_rows": 0,
            "waiver_rows": 0,
            "strict_trigger_required": False,
            "single_waiver_fallback_allowed": allow_single_waiver_fallback,
        }

    text = progress_path.read_text(encoding="utf-8")

    task_plan_text: str | None = None
    if task_plan_path is not None:
        if not task_plan_path.is_file():
            return {
                "status": "fail",
                "errors": [f"task plan file not found: {task_plan_path}"],
                "warnings": [],
                "ledger_rows": 0,
                "waiver_rows": 0,
                "strict_trigger_required": False,
                "single_waiver_fallback_allowed": allow_single_waiver_fallback,
            }
        task_plan_text = task_plan_path.read_text(encoding="utf-8")

    strict_required = strict_trigger and strict_trigger_required(task_plan_text)
    ledger_rows = real_rows(extract_table(text, "## Final Evidence Ledger"), "acceptance_id")
    waiver_rows = real_rows(extract_table(text, "## Verification Waivers"), "check")
    tooling_gap_debt_rows = real_rows(extract_table(text, "## Tooling Gap Debt"), "tool_class")

    if strict_required and not ledger_rows:
        errors.append("strict trigger requires Final Evidence Ledger rows for high/release/external-system tasks")

    valid_waivers: list[dict[str, str]] = []
    for waiver in waiver_rows:
        complete, waiver_errors = waiver_complete(waiver)
        if complete:
            valid_waivers.append(waiver)
        errors.extend(waiver_errors)

    repeated_classes = repeated_waiver_classes(valid_waivers)
    repeated_signals = repeated_waiver_signals(valid_waivers)
    missing_repeated_debt = tooling_gap_debt_missing_repeated_classes(tooling_gap_debt_rows, repeated_classes)
    if strict_required and repeated_signals and missing_repeated_debt:
        errors.append(
            "strict trigger repeated waiver signals require Tooling Gap Debt row with repeat count >= 2: "
            + ", ".join(repeated_signals)
            + "; missing matching classes: "
            + ", ".join(missing_repeated_debt)
        )

    for row in ledger_rows:
        acceptance_id = row.get("acceptance_id", "")
        final_status = clean_cell(row.get("final_status", "")).upper()
        supplemental = row.get("supplemental_evidence", "")
        artifact = row.get("artifact", "")

        if final_status not in FINAL_STATUSES:
            errors.append(f"ledger {acceptance_id}: invalid final status {final_status or '<empty>'}")
            continue

        if final_status == "PASS" and not has_replayable_pass_evidence(supplemental, artifact):
            errors.append(
                f"ledger {acceptance_id}: PASS requires replayable artifact/manifest/API/screenshot/trace path or true manual QA note"
            )
        if final_status == "PASS":
            for field_name, field_value in (("supplemental evidence", supplemental), ("artifact", artifact)):
                if manual_note_with_command_signal(field_value):
                    errors.append(
                        f"ledger {acceptance_id}: {field_name} is a manual note for command/terminal evidence; "
                        "capture the command under .agent-state/runs/<run_id>/manifest.json instead"
                    )
        if final_status == "PASS" and require_existing_artifacts:
            errors.extend(evidence_path_errors(progress_path.parent, artifact, f"ledger {acceptance_id} artifact"))
            errors.extend(evidence_path_errors(progress_path.parent, supplemental, f"ledger {acceptance_id} supplemental evidence"))

        if final_status == "WAIVED":
            waiver = find_matching_waiver(
                valid_waivers,
                acceptance_id,
                allow_single_waiver_fallback=allow_single_waiver_fallback and not strict_required,
            )
            if waiver is None:
                errors.append(f"ledger {acceptance_id}: WAIVED requires matching complete Verification Waivers row")

        if final_status in {"FAILED", "BLOCKED"}:
            notes = row.get("notes", "")
            if is_placeholder(notes):
                warnings.append(f"ledger {acceptance_id}: {final_status} should include notes for closure")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "ledger_rows": len(ledger_rows),
        "waiver_rows": len(waiver_rows),
        "tooling_gap_debt_rows": len(tooling_gap_debt_rows),
        "repeated_waiver_signals": repeated_signals,
        "strict_trigger_required": strict_required,
        "single_waiver_fallback_allowed": allow_single_waiver_fallback and not strict_required,
        "require_existing_artifacts": require_existing_artifacts,
    }


def emit_text(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"ledger_rows: {payload.get('ledger_rows', 0)}")
    print(f"waiver_rows: {payload.get('waiver_rows', 0)}")
    print(f"strict_trigger_required: {str(payload.get('strict_trigger_required', False)).lower()}")
    if payload["warnings"]:
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    if payload["errors"]:
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Final Evidence Ledger and Verification Waivers structure.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file to inspect.")
    parser.add_argument("--task-plan", help="Optional task_plan.md path used with --strict-trigger.")
    parser.add_argument("--strict-trigger", action="store_true", help="Fail if high/release/external-system tasks omit Final Evidence Ledger rows.")
    parser.add_argument(
        "--allow-single-waiver-fallback",
        action="store_true",
        help="Compat mode: allow one complete waiver to match one or more WAIVED ledger rows outside strict mode.",
    )
    parser.add_argument(
        "--require-existing-artifacts",
        action="store_true",
        help="Fail PASS rows when repo-local evidence paths do not exist. Use for current high/release runs, not raw legacy archives.",
    )
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
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = root / progress_path
    task_plan_path = Path(args.task_plan) if args.task_plan else None
    if task_plan_path is not None and not task_plan_path.is_absolute():
        task_plan_path = root / task_plan_path

    payload = validate(
        progress_path,
        task_plan_path=task_plan_path,
        strict_trigger=args.strict_trigger,
        allow_single_waiver_fallback=args.allow_single_waiver_fallback,
        require_existing_artifacts=args.require_existing_artifacts,
        check_template=args.check_template,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        emit_text(payload)
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
