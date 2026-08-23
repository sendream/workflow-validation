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


PLACEHOLDERS = {"", "待填写", "none", "missing", "pending", "required"}
PLACEHOLDER_OPTIONS = {
    "not-needed",
    "promote",
    "defer",
    "none",
    "pending",
    "pass",
    "fail",
    "failed",
    "waived",
    "manual",
    "blocked",
    "not_applicable",
    "s0",
    "s1",
    "s2",
    "s3",
}
FINAL_STATUSES = wr.FINAL_EVIDENCE_STATUSES
STALE_VERIFICATION_STATUSES = {
    "pending",
    "planned",
    "todo",
    "not-run",
    "not run",
    "missing",
    "required",
    "待填写",
    "未运行",
    "计划中",
}
CASE_CLASSES = {
    "positive",
    "negative",
    "boundary",
    "regression",
    "compatibility",
    "permission-deny",
    "failure-path",
    "property",
    "contract",
    "not-needed",
}
RISK_CASE_CLASSES = CASE_CLASSES - {"positive", "not-needed"}
RECONCILIATION_STATUSES = {
    "pass",
    "mismatch",
    "needs-human-check",
    "waived",
    "not-needed",
}
RECONCILIATION_BLOCKING_STATUSES = {"mismatch", "needs-human-check"}
UNRESOLVED_TEST_ORACLES = {"needs-human-check"}


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_key(value: str) -> str:
    return clean_cell(value).lower().replace(" ", "_").replace("/", "_")


def is_placeholder(value: str) -> bool:
    normalized = clean_cell(value).lower()
    if normalized in PLACEHOLDERS or "<run_id>" in normalized or "待填写" in normalized:
        return True
    if " / " in normalized:
        parts = [part.strip().replace("-", "_") for part in normalized.split("/")]
        return any(part in PLACEHOLDER_OPTIONS for part in parts)
    return False


def is_template_path(path: Path) -> bool:
    return ".agents/templates" in path.as_posix()


def is_not_needed(value: str) -> bool:
    return clean_cell(value).lower() == "not-needed"


def get_first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row:
            return row.get(key, "")
    return ""


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


def extract_named_section_value(markdown_text: str, heading: str) -> str:
    return "\n".join(extract_section(markdown_text, heading)).lower()


def extract_risk_tier(markdown_text: str) -> str | None:
    return wr.extract_risk_tier(markdown_text)


def strict_trigger_required(task_plan_text: str | None) -> bool:
    if task_plan_text is None:
        return False
    tier = extract_risk_tier(task_plan_text)
    if tier is not None:
        return tier in {"high", "release"}
    return False


def linked_scenario_ids(value: str) -> list[str]:
    value = clean_cell(value)
    if is_placeholder(value) or is_not_needed(value):
        return []
    return [part.strip() for part in value.replace("，", ",").split(",") if part.strip()]


def linked_ids(value: str) -> list[str]:
    value = clean_cell(value)
    if is_placeholder(value) or is_not_needed(value):
        return []
    return [part.strip() for part in value.replace("，", ",").split(",") if part.strip()]


def token_set(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.split(r"[^A-Za-z0-9_.:-]+", clean_cell(value))
        if token
    }


def stable_id_tokens(value: str) -> set[str]:
    """Return identifier-like tokens, excluding descriptive words.

    Acceptance cells often use "A1 login smoke" while ledgers use "A1".
    Matching on every shared word is too broad; only tokens containing both
    letters and digits are treated as stable IDs.
    """
    return {
        token
        for token in token_set(value)
        if re.search(r"[a-zA-Z]", token) and re.search(r"\d", token)
    }


def find_matching_waiver(waivers: list[dict[str, str]], acceptance_id: str) -> dict[str, str] | None:
    normalized = clean_cell(acceptance_id).lower()
    for waiver in waivers:
        check = clean_cell(waiver.get("check", "")).lower()
        if check == normalized or normalized in token_set(check):
            return waiver
    return None


def normalize_case_class(value: str) -> str:
    return clean_cell(value).lower().replace("_", "-")


def normalize_dash_value(value: str) -> str:
    return re.sub(r"[\s_]+", "-", clean_cell(value).lower()).strip("-")


def normalize_case_classes(value: str) -> set[str]:
    value = clean_cell(value)
    if is_placeholder(value) or is_not_needed(value):
        return set()
    classes: set[str] = set()
    for part in re.split(r"[,，;/]+", value):
        normalized = normalize_case_class(part)
        if normalized and not is_placeholder(normalized) and not is_not_needed(normalized):
            classes.add(normalized)
    return classes


def must_verify(value: str) -> bool:
    normalized = clean_cell(value).lower().replace("_", "-")
    return normalized in {"yes", "required", "must", "block", "blocking", "true"}


def matching_verification_rows(verification_rows: list[dict[str, str]], verification_id: str) -> list[dict[str, str]]:
    normalized = clean_cell(verification_id).lower()
    matches: list[dict[str, str]] = []
    for row in verification_rows:
        item_id = clean_cell(row.get("acceptance___risk", "")).lower()
        if item_id == normalized or normalized in token_set(item_id):
            matches.append(row)
    return matches


def verification_id_defined(verification_rows: list[dict[str, str]], verification_id: str) -> bool:
    return bool(matching_verification_rows(verification_rows, verification_id))


def matching_ledger_rows(ledger_rows: list[dict[str, str]], acceptance_id: str) -> list[dict[str, str]]:
    normalized = clean_cell(acceptance_id).lower()
    acceptance_ids = stable_id_tokens(normalized)
    matches: list[dict[str, str]] = []
    for row in ledger_rows:
        item_id = clean_cell(row.get("acceptance_id", "")).lower()
        item_ids = stable_id_tokens(item_id)
        if item_id == normalized or (acceptance_ids and item_ids and bool(item_ids & acceptance_ids)):
            matches.append(row)
    return matches


def final_status_verified(row: dict[str, str]) -> bool:
    return clean_cell(row.get("final_status", "")).upper() in {"PASS", "MANUAL", "WAIVED"}


def final_status_pass(row: dict[str, str]) -> bool:
    return clean_cell(row.get("final_status", "")).upper() == "PASS"


def matching_ledger_rows_by_scenario(ledger_rows: list[dict[str, str]], scenario_ids: list[str]) -> list[dict[str, str]]:
    wanted = {clean_cell(scenario_id).lower() for scenario_id in scenario_ids if not is_placeholder(scenario_id)}
    if not wanted:
        return []
    matches: list[dict[str, str]] = []
    for row in ledger_rows:
        row_scenarios = {clean_cell(scenario_id).lower() for scenario_id in linked_scenario_ids(row.get("scenario_id", ""))}
        if row_scenarios & wanted:
            matches.append(row)
    return matches


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[int] = set()
    unique_rows: list[dict[str, str]] = []
    for row in rows:
        row_id = id(row)
        if row_id in seen:
            continue
        seen.add(row_id)
        unique_rows.append(row)
    return unique_rows


def matching_reconciliation_ledgers(
    ledger_rows: list[dict[str, str]],
    linked_acceptance: str,
    scenario_ids: list[str],
) -> list[dict[str, str]]:
    acceptance_ids = linked_ids(linked_acceptance)
    if acceptance_ids:
        matches: list[dict[str, str]] = []
        for acceptance_id in acceptance_ids:
            matches.extend(matching_ledger_rows(ledger_rows, acceptance_id))
        return dedupe_rows(matches)
    return matching_ledger_rows_by_scenario(ledger_rows, scenario_ids)


def known_acceptance_ids(
    verification_rows: list[dict[str, str]],
    ledger_rows: list[dict[str, str]],
    linked_acceptance: str,
) -> list[str]:
    known: list[str] = []
    for acceptance_id in linked_ids(linked_acceptance):
        if matching_verification_rows(verification_rows, acceptance_id) or matching_ledger_rows(ledger_rows, acceptance_id):
            known.append(acceptance_id)
    return known


def known_scenario_ids(scenarios: set[str], scenario_ids: list[str]) -> list[str]:
    scenario_lookup = {clean_cell(scenario).lower() for scenario in scenarios}
    return [scenario_id for scenario_id in scenario_ids if clean_cell(scenario_id).lower() in scenario_lookup]


def stale_verification_value(value: str) -> bool:
    normalized = clean_cell(value).lower().replace("_", "-")
    return normalized in STALE_VERIFICATION_STATUSES


def stale_verification_fields(row: dict[str, str]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for key in ("status", "matrix_status", "evidence", "result"):
        value = clean_cell(row.get(key, ""))
        if stale_verification_value(value):
            fields.append((key, value))
    return fields


def validate(
    task_plan_path: Path,
    progress_path: Path | None = None,
    strict_trigger: bool = False,
    check_template: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not task_plan_path.is_file():
        return {"status": "fail", "errors": [f"task plan file not found: {task_plan_path}"], "warnings": []}

    if is_template_path(task_plan_path) and not check_template:
        return {
            "status": "skipped",
            "errors": [],
            "warnings": ["template path detected; pass --check-template to validate template placeholders intentionally"],
            "strict_trigger_required": False,
            "scenario_rows": 0,
            "example_rows": 0,
            "verification_rows": 0,
            "ledger_rows": 0,
        }

    task_text = task_plan_path.read_text(encoding="utf-8")
    progress_text = progress_path.read_text(encoding="utf-8") if progress_path and progress_path.is_file() else ""
    strict_required = strict_trigger and strict_trigger_required(task_text)

    scenario_rows = real_rows(extract_table(task_text, "## Behavior Scenarios"), "scenario_id")
    scenarios = {clean_cell(row.get("scenario_id", "")) for row in scenario_rows if not is_not_needed(row.get("scenario_id", ""))}
    example_rows = real_rows(extract_table(task_text, "## Example Table"), "example_id")

    verification_rows = real_rows(extract_table(task_text, "## Verification Matrix"), "acceptance___risk")
    acceptance_rows = real_rows(extract_table(task_text, "## Acceptance Evidence Map"), "acceptance_item")
    ledger_rows = real_rows(extract_table(progress_text, "## Final Evidence Ledger"), "acceptance_id") if progress_text else []
    waiver_rows = real_rows(extract_table(progress_text, "## Verification Waivers"), "check") if progress_text else []
    reconciliation_rows = real_rows(extract_table(progress_text, "## Requirement Reconciliation"), "check_id") if progress_text else []

    if strict_required and not verification_rows:
        errors.append("strict trigger requires Verification Matrix rows for high/release tasks")

    if strict_required and verification_rows and not scenario_rows:
        errors.append("strict trigger requires Behavior Scenarios rows or explicit not-needed row for high/release traceability")

    if strict_required and progress_text and not ledger_rows:
        errors.append("strict trigger requires Final Evidence Ledger rows when progress.md is provided")

    referenced_scenarios: set[str] = set()
    for rows in (verification_rows, acceptance_rows, ledger_rows):
        for row in rows:
            for scenario_id in linked_scenario_ids(row.get("scenario_id", "")):
                referenced_scenarios.add(scenario_id)

    planned_case_classes: set[str] = set()
    evidence_case_classes: set[str] = set()
    scenario_case_classes: dict[str, set[str]] = {}

    for row in scenario_rows:
        scenario_id = clean_cell(row.get("scenario_id", ""))
        if is_not_needed(scenario_id):
            continue
        acceptance_id = row.get("acceptance_id", "")
        outcome = row.get("then___observable_outcome", "") or row.get("then_observable_outcome", "")
        evidence_method = row.get("evidence_method", "")
        case_class = normalize_case_class(row.get("case_class", ""))
        case_classes = normalize_case_classes(row.get("case_class", ""))
        if strict_required and is_placeholder(acceptance_id):
            errors.append(f"scenario {scenario_id}: acceptance_id is missing")
        if strict_required and is_placeholder(outcome):
            errors.append(f"scenario {scenario_id}: observable outcome is missing")
        if strict_required and is_placeholder(evidence_method):
            errors.append(f"scenario {scenario_id}: evidence method is missing")
        if strict_required and is_placeholder(case_class):
            errors.append(f"scenario {scenario_id}: case_class is missing")
        invalid_case_classes = sorted(case_classes - CASE_CLASSES)
        for invalid_case_class in invalid_case_classes:
            errors.append(f"scenario {scenario_id}: invalid case_class {invalid_case_class}")
        if case_classes:
            planned_case_classes.update(case_classes)
            scenario_case_classes[scenario_id] = case_classes
        if strict_required and scenario_id not in referenced_scenarios:
            errors.append(f"scenario {scenario_id}: missing Verification Matrix / Evidence reference")

    for row in example_rows:
        example_id = clean_cell(row.get("example_id", ""))
        if is_not_needed(example_id):
            continue
        case_type = normalize_case_class(get_first(row, "case_type", "case_class"))
        case_types = normalize_case_classes(get_first(row, "case_type", "case_class"))
        oracle = get_first(
            row,
            "oracle____expected_observable",
            "oracle___expected_observable",
            "oracle_expected_observable",
            "expected_result",
        )
        linked_scenario_value = get_first(row, "linked_scenario", "scenario_id")
        linked_example_scenarios = linked_scenario_ids(linked_scenario_value)
        covered_by = get_first(
            row,
            "covered_by_acceptance_risk_id",
            "covered_by_acceptance___risk_id",
            "covered_by_verification_id",
            "verification_id",
            "linked_verification_id",
        )
        must_value = get_first(row, "must_verify")
        if strict_required and is_placeholder(must_value):
            errors.append(f"example {example_id}: must_verify is missing")
        invalid_case_types = sorted(case_types - CASE_CLASSES)
        for invalid_case_type in invalid_case_types:
            errors.append(f"example {example_id}: invalid case_type {invalid_case_type}")
        if case_types:
            planned_case_classes.update(case_types)
        if must_verify(must_value):
            if is_placeholder(case_type):
                errors.append(f"example {example_id}: must_verify requires case_type")
            if is_placeholder(oracle):
                errors.append(f"example {example_id}: must_verify requires oracle / expected observable")
            if is_placeholder(covered_by):
                errors.append(f"example {example_id}: must_verify requires covered_by acceptance/risk id")
            if not linked_example_scenarios:
                errors.append(f"example {example_id}: must_verify requires linked scenario")
            for scenario_id in linked_example_scenarios:
                if scenario_id not in scenarios:
                    errors.append(f"example {example_id}: linked scenario {scenario_id} is not defined in Behavior Scenarios")
                scenario_case = scenario_case_classes.get(scenario_id, set())
                if case_types and scenario_case and not (case_types & scenario_case):
                    errors.append(f"example {example_id}: case_type does not match linked scenario {scenario_id} case_class")
            for verification_id in linked_ids(covered_by):
                verification_matches = matching_verification_rows(verification_rows, verification_id)
                if not verification_matches:
                    errors.append(f"example {example_id}: covered_by acceptance/risk id {verification_id} is not defined in Verification Matrix")
                    continue
                matched_matrix_case = False
                matched_matrix_scenario = False
                for verification_row in verification_matches:
                    matrix_case_classes = normalize_case_classes(verification_row.get("case_class", ""))
                    matrix_scenarios = set(linked_scenario_ids(verification_row.get("scenario_id", "")))
                    if not case_types or not matrix_case_classes or case_types & matrix_case_classes:
                        matched_matrix_case = True
                    if not linked_example_scenarios or not matrix_scenarios or matrix_scenarios & set(linked_example_scenarios):
                        matched_matrix_scenario = True
                if not matched_matrix_case:
                    errors.append(f"example {example_id}: case_type does not match covered Verification Matrix case_class")
                if not matched_matrix_scenario:
                    errors.append(f"example {example_id}: linked scenario is not covered by covered Verification Matrix row")
                verified_ledger_rows = [ledger for ledger in matching_ledger_rows(ledger_rows, verification_id) if final_status_verified(ledger)]
                if not verified_ledger_rows:
                    errors.append(f"example {example_id}: covered acceptance/risk id {verification_id} has no PASS/MANUAL/WAIVED Final Evidence Ledger row")
                elif case_types:
                    verified_cases = set()
                    for ledger in verified_ledger_rows:
                        verified_cases.update(normalize_case_classes(ledger.get("case_class", "")))
                    if verified_cases and not (case_types & verified_cases):
                        errors.append(f"example {example_id}: case_type does not match Final Evidence Ledger case_class")

    for source, rows, id_key in (
        ("Verification Matrix", verification_rows, "acceptance___risk"),
        ("Acceptance Evidence Map", acceptance_rows, "acceptance_item"),
        ("Final Evidence Ledger", ledger_rows, "acceptance_id"),
    ):
        for row in rows:
            item_id = clean_cell(row.get(id_key, ""))
            scenario_value = row.get("scenario_id", "")
            case_class = normalize_case_class(row.get("case_class", ""))
            case_classes = normalize_case_classes(row.get("case_class", ""))
            if is_placeholder(scenario_value):
                if strict_required:
                    errors.append(f"{source} {item_id}: scenario_id is missing; use a scenario id or explicit not-needed")
                continue
            if is_not_needed(scenario_value):
                continue
            if strict_required and is_placeholder(case_class):
                errors.append(f"{source} {item_id}: case_class is missing")
            invalid_case_classes = sorted(case_classes - CASE_CLASSES)
            for invalid_case_class in invalid_case_classes:
                errors.append(f"{source} {item_id}: invalid case_class {invalid_case_class}")
            if case_classes:
                planned_case_classes.update(case_classes)
            for scenario_id in linked_scenario_ids(scenario_value):
                if scenario_id not in scenarios:
                    errors.append(f"{source} {item_id}: scenario_id {scenario_id} is not defined in Behavior Scenarios")
                    continue
                scenario_case = scenario_case_classes.get(scenario_id, set())
                if len(linked_scenario_ids(scenario_value)) == 1 and case_classes and scenario_case and not (case_classes & scenario_case):
                    errors.append(f"{source} {item_id}: case_class does not match scenario {scenario_id} case_class")

            final_status = clean_cell(row.get("final_status", "")).upper()
            if source == "Final Evidence Ledger" and final_status == "WAIVED":
                if find_matching_waiver(waiver_rows, item_id) is None:
                    errors.append(f"Final Evidence Ledger {item_id}: WAIVED scenario requires matching Verification Waivers row")
            if source == "Final Evidence Ledger" and final_status and final_status not in FINAL_STATUSES:
                errors.append(f"Final Evidence Ledger {item_id}: invalid final status {final_status}")
            if source == "Final Evidence Ledger" and final_status_verified(row):
                evidence_case_classes.update(case_classes)

    for verification_row in verification_rows:
        item_id = clean_cell(verification_row.get("acceptance___risk", ""))
        if not item_id:
            continue
        test_oracle = get_first(
            verification_row,
            "test_oracle___independence",
            "test_oracle_independence",
            "oracle_independence",
            "oracle",
        )
        if strict_required and must_verify(verification_row.get("blocking", "")) and (
            is_placeholder(test_oracle) or is_not_needed(test_oracle)
        ):
            errors.append(f"Verification Matrix {item_id}: blocking row requires test oracle / independence")
        if strict_required and must_verify(verification_row.get("blocking", "")) and not matching_ledger_rows(ledger_rows, item_id):
            errors.append(f"Verification Matrix {item_id}: blocking acceptance/risk has no matching Final Evidence Ledger row")
            continue
        verified_ledger_rows = [ledger for ledger in matching_ledger_rows(ledger_rows, item_id) if final_status_verified(ledger)]
        if not verified_ledger_rows:
            continue
        if (
            strict_required
            and normalize_dash_value(test_oracle) in UNRESOLVED_TEST_ORACLES
            and any(final_status_pass(ledger) for ledger in verified_ledger_rows)
        ):
            errors.append(
                f"Verification Matrix {item_id}: test oracle / independence remains {normalize_dash_value(test_oracle)} while Final Evidence Ledger has PASS"
            )
        for key, value in stale_verification_fields(verification_row):
            errors.append(
                f"Verification Matrix {item_id}: {key} remains {value} while Final Evidence Ledger has PASS/MANUAL/WAIVED; update the plan matrix before closeout"
            )

    if strict_required and ledger_rows and "positive" in evidence_case_classes and not (evidence_case_classes & RISK_CASE_CLASSES):
        errors.append("strict trigger with positive Final Evidence Ledger requires at least one non-positive PASS/MANUAL/WAIVED case_class")

    for row in reconciliation_rows:
        check_id = clean_cell(row.get("check_id", ""))
        status = normalize_dash_value(get_first(row, "alignment_status", "status"))
        if is_placeholder(status):
            continue
        if status not in RECONCILIATION_STATUSES:
            message = f"Requirement Reconciliation {check_id}: unknown alignment_status {status}"
            if strict_required:
                errors.append(message)
            else:
                warnings.append(message)
            continue
        if status not in RECONCILIATION_BLOCKING_STATUSES:
            continue
        linked_acceptance = get_first(row, "requirement_id___acceptance_id", "acceptance_id", "requirement_id")
        scenario_ids = linked_scenario_ids(row.get("scenario_id", ""))
        acceptance_ids = linked_ids(linked_acceptance)
        known_acceptances = known_acceptance_ids(verification_rows, ledger_rows, linked_acceptance)
        known_scenarios = known_scenario_ids(scenarios, scenario_ids)
        if strict_required and not known_acceptances and not known_scenarios:
            errors.append(
                f"Requirement Reconciliation {check_id}: alignment_status {status} requires linked acceptance_id or scenario_id"
            )
            continue
        unknown_acceptances = [
            acceptance_id
            for acceptance_id in acceptance_ids
            if acceptance_id not in known_acceptances
        ]
        unknown_scenarios = [
            scenario_id
            for scenario_id in scenario_ids
            if scenario_id not in known_scenarios
        ]
        if strict_required and unknown_acceptances:
            errors.append(
                f"Requirement Reconciliation {check_id}: unknown linked acceptance_id(s): {', '.join(unknown_acceptances)}"
            )
            continue
        if strict_required and unknown_scenarios:
            errors.append(
                f"Requirement Reconciliation {check_id}: unknown linked scenario_id(s): {', '.join(unknown_scenarios)}"
            )
            continue
        if known_acceptances:
            matching_ledgers = []
            for acceptance_id in known_acceptances:
                matching_ledgers.extend(matching_ledger_rows(ledger_rows, acceptance_id))
            matching_ledgers = dedupe_rows(matching_ledgers)
        else:
            matching_ledgers = matching_ledger_rows_by_scenario(ledger_rows, known_scenarios)
        pass_ledgers = [ledger for ledger in matching_ledgers if final_status_pass(ledger)]
        if pass_ledgers:
            ledger_ids = ", ".join(sorted({clean_cell(ledger.get("acceptance_id", "")) for ledger in pass_ledgers}))
            errors.append(
                f"Requirement Reconciliation {check_id}: alignment_status {status} conflicts with PASS Final Evidence Ledger rows: {ledger_ids}"
            )

    if not progress_text and strict_required:
        warnings.append("progress file missing or not provided; Final Evidence Ledger traceability was not checked")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "strict_trigger_required": strict_required,
        "scenario_rows": len(scenario_rows),
        "example_rows": len(example_rows),
        "case_classes": sorted(planned_case_classes | evidence_case_classes),
        "planned_case_classes": sorted(planned_case_classes),
        "evidence_case_classes": sorted(evidence_case_classes),
        "verification_rows": len(verification_rows),
        "ledger_rows": len(ledger_rows),
        "reconciliation_rows": len(reconciliation_rows),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate requirement-to-scenario-to-evidence traceability.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-plan", default="task_plan.md", help="Task plan markdown file.")
    parser.add_argument("--progress", default="progress.md", help="Progress markdown file.")
    parser.add_argument("--strict-trigger", action="store_true", help="Apply high/release traceability requirements.")
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
        progress_path=progress_path,
        strict_trigger=args.strict_trigger,
        check_template=args.check_template,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        print(f"strict_trigger_required: {str(payload.get('strict_trigger_required', False)).lower()}")
        for warning in payload.get("warnings", []):
            print(f"warning: {warning}")
        for error in payload.get("errors", []):
            print(f"error: {error}")
    return 0 if payload["status"] in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
