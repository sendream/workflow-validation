#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Callable
from typing import Any


FALSIFICATION_OUTCOMES = {"excluded", "not-reproduced", "not-applicable"}
PLACEHOLDER_VALUES = {
    "",
    "n/a",
    "na",
    "missing",
    "none",
    "not-applicable",
    "not-needed",
    "not needed",
    "optional",
    "pending",
    "required",
    "tbd",
    "todo",
    "unknown",
    "待填写",
}


def _clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _normalized(value: Any) -> str:
    return _clean(value).lower()


def _placeholder(value: Any, *, allow_not_applicable: bool = False) -> bool:
    normalized = _normalized(value)
    if allow_not_applicable and normalized == "not-applicable":
        return False
    return normalized in PLACEHOLDER_VALUES


def validate_falsification_attempts(
    payload: dict[str, Any],
    *,
    context: str,
    evidence_errors: Callable[[str], list[str]],
) -> list[str]:
    """Validate the shared pass/falsification result contract.

    Evidence lookup stays validator-specific because standalone packets and
    campaign packets resolve their controlled roots differently.
    """

    verdict = _normalized(payload.get("verdict"))
    attempts = payload.get("falsification_attempts")
    if attempts is None and verdict != "pass":
        return []
    if not isinstance(attempts, list) or not attempts:
        if verdict == "pass":
            return [f"{context}: verdict=pass requires non-empty falsification_attempts"]
        return [f"{context}: falsification_attempts must be a non-empty list when present"]

    errors: list[str] = []
    outcomes: list[str] = []
    for index, attempt in enumerate(attempts, start=1):
        item_context = f"{context}: falsification_attempts[{index}]"
        if not isinstance(attempt, dict):
            errors.append(f"{item_context} must be an object")
            continue

        clean_values: dict[str, str] = {}
        for field in ("hypothesis", "probe", "evidence", "outcome"):
            raw_value = attempt.get(field)
            value = _clean(raw_value) if isinstance(raw_value, str) else ""
            clean_values[field] = value
            if not isinstance(raw_value, str) or _placeholder(
                value,
                allow_not_applicable=field == "outcome",
            ):
                errors.append(f"{item_context} {field} is missing or placeholder")

        outcome = _normalized(clean_values["outcome"])
        outcomes.append(outcome)
        if (
            clean_values["outcome"]
            and not _placeholder(clean_values["outcome"], allow_not_applicable=True)
            and outcome not in FALSIFICATION_OUTCOMES
        ):
            errors.append(
                f"{item_context} outcome must be excluded/not-reproduced/not-applicable"
            )

        evidence = clean_values["evidence"]
        if evidence and not _placeholder(evidence):
            for binding_error in evidence_errors(evidence):
                errors.append(f"{item_context} {binding_error}")

    if (
        verdict == "pass"
        and outcomes
        and all(outcome == "not-applicable" for outcome in outcomes)
    ):
        errors.append(f"{context}: verdict=pass falsification_attempts cannot all be not-applicable")
    return errors
