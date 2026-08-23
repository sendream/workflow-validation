#!/usr/bin/env python3
"""Pure, report-only contracts used by the workflow-reference selector.

This module deliberately has no project I/O.  It keeps prompt-signal parsing and
budget semantics testable while leaving project-specific file selection in
``context-select.py``.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


_SIGNALS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("risk", "release", ("release", "deploy", "发布", "部署", "交付", "上线", "发版")),
    ("impact", "external-system", ("external-system", "external system", "外部系统", "production", "prod")),
    ("impact", "cross-package", ("cross-package", "cross module", "跨模块", "跨层", "全仓")),
)
_NEGATED_ENGLISH_SUFFIX_RE = re.compile(
    r"(?:\bnot|\bno|\bwithout|\bnever)(?:\s+(?:a|an|the|in|on|to|for|any|this|that|our))?\s*$",
    re.IGNORECASE,
)
_NEGATED_CHINESE_SUFFIX_RE = re.compile(
    r"(?:不涉及|未涉及|不需要|不允许|不打算|不计划|不必|不用|不会|不能|不要|不应|不在|不是|没有|无需|禁止|不|未|无|非)[\s,，、:：]*$"
)


def _negated_prefix(window: str) -> str | None:
    """Return a bounded, locally adjacent negation prefix when present."""
    match = _NEGATED_ENGLISH_SUFFIX_RE.search(window)
    if match:
        return match.group(0)
    match = _NEGATED_CHINESE_SUFFIX_RE.search(window)
    return match.group(0) if match else None


def _is_negated(prompt: str, start: int) -> bool:
    """Return whether a bounded local window negates the following signal."""
    window = prompt[max(0, start - 12) : start]
    return _negated_prefix(window) is not None


def _negated_match_text(prompt: str, start: int, end: int) -> str:
    """Preserve the locally negated phrase in report-only routing evidence."""
    window = prompt[max(0, start - 12) : start]
    prefix = _negated_prefix(window) or ""
    return f"{prefix}{prompt[start:end]}"


def _phrase_matches(prompt: str, phrase: str) -> Iterable[re.Match[str]]:
    """Find a signal phrase without accepting ASCII identifier substrings."""
    escaped = re.escape(phrase)
    if any(char.isascii() and char.isalnum() for char in phrase):
        escaped = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return re.finditer(escaped, prompt, flags=re.IGNORECASE)


def classify_prompt_signals(prompt: str) -> dict[str, list[str]]:
    """Return bounded positive and negated prompt candidates without authority.

    Entries are stable, human-readable ``kind:value:matched-text`` strings so
    callers can report why a prompt needs confirmation without storing raw
    prompt text elsewhere.
    """
    positive: list[str] = []
    negated: list[str] = []
    seen: set[str] = set()
    for kind, value, phrases in _SIGNALS:
        for phrase in phrases:
            for match in _phrase_matches(prompt, phrase):
                matched_text = match.group(0)
                negated_match = _is_negated(prompt, match.start())
                if negated_match:
                    matched_text = _negated_match_text(prompt, match.start(), match.end())
                entry = f"{kind}:{value}:{matched_text}"
                if entry in seen:
                    continue
                seen.add(entry)
                (negated if negated_match else positive).append(entry)
    return {"positive": positive, "negated": negated}


def signal_values(signals: dict[str, list[str]], *, kind: str, polarity: str = "positive") -> set[str]:
    """Extract candidate enum values from ``classify_prompt_signals`` output."""
    values: set[str] = set()
    for entry in signals.get(polarity, []):
        parts = entry.split(":", 2)
        if len(parts) == 3 and parts[0] == kind:
            values.add(parts[1])
    return values


def _budget_status(value: int, budget_tokens: int, *, unresolved: bool) -> str:
    if unresolved:
        return "unresolved"
    return "over-budget" if value > budget_tokens else "within-budget"


def build_budget_report(
    *,
    initial_load_estimate: int,
    current_stage_estimate: int,
    forecast_total_estimate: int,
    budget_tokens: int,
    measurement_status: str,
    required_stages: Iterable[dict[str, Any]],
    unresolved: bool,
) -> dict[str, Any]:
    """Build unambiguous staged budget output with one-release aliases.

    File-size estimates are intentionally labelled ``inferred``.  The legacy
    fields remain only as compatibility aliases so existing callers do not
    silently regain the old per-stage-only ``status`` semantics.
    """
    stages = list(required_stages)
    over_budget_stages = [stage.get("stage", "") for stage in stages if int(stage.get("tokens", 0)) > budget_tokens]
    initial_status = _budget_status(initial_load_estimate, budget_tokens, unresolved=unresolved)
    current_status = _budget_status(current_stage_estimate, budget_tokens, unresolved=unresolved)
    forecast_status = _budget_status(forecast_total_estimate, budget_tokens, unresolved=unresolved)
    split_stage_suggestion = "not-needed"
    if forecast_status == "over-budget":
        split_stage_suggestion = "read the initial load first; defer conditional references until the matching gate is reached"
    return {
        "initial_load_estimate": initial_load_estimate,
        "current_stage_estimate": current_stage_estimate,
        "forecast_total_estimate": forecast_total_estimate,
        "reserved_system_and_tools": {"estimate": None, "measurement_status": "unavailable"},
        "measurement_status": measurement_status,
        "budget_tokens": budget_tokens,
        "initial_status": initial_status,
        "current_stage_status": current_status,
        "forecast_status": forecast_status,
        "required_stages": stages,
        "over_budget_stages": over_budget_stages,
        "split_stage_suggestion": split_stage_suggestion,
        "compatibility_aliases": {
            "expires_after": "next selector schema revision",
            "fields": ["must_read_tokens", "conditional_read_tokens", "estimated_tokens", "status"],
        },
        "must_read_tokens": initial_load_estimate,
        "conditional_read_tokens": max(0, forecast_total_estimate - initial_load_estimate),
        "estimated_tokens": forecast_total_estimate,
        "status": forecast_status,
    }
