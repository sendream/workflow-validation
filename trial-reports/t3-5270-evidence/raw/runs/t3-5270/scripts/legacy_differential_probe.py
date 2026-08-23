#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from unittest.mock import patch

import black
import black.linegen
from black.lines import Line
from black.mode import Mode

LINE_LENGTHS = (1, 20, 40, 79, 80, 81, 88, 100)
BODY_FACTORIES: dict[str, Callable[[int], str]] = {
    "number": lambda index: str(index % 7),
    "increasing-number": lambda index: str(10 ** (index // 10) + index),
    "name": lambda index: f"key{index % 7}",
    "increasing-name": lambda index: "key" + "x" * (index // 10 + 1),
    "increasing-wide-name": lambda index: "名" * (index // 10 + 1),
    "string": lambda index: repr(f"k{index % 7}"),
    "wide-string": lambda index: repr(f"wide_key_{index % 7}"),
    "increasing-wide-string": lambda index: repr("字" * (index // 10 + 1)),
    "mixed": lambda index: (
        str(index % 7),
        f"key{index % 7}",
        repr(f"k{index % 7}"),
    )[index % 3],
}
ASSIGNMENTS = {
    "top-level": "result = ",
    "annotated": "result: list[int] = ",
    "chained": "holder = result = ",
    "indented": "if True:\n    result = ",
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compare(source: str, mode: Mode) -> tuple[bool, bool, str, str]:
    original = black.linegen._batch_split_flat_subscript_chain
    accepted = False

    def tracked(line: Line, current_mode: Mode) -> Iterator[Line]:
        nonlocal accepted
        lines = list(original(line, current_mode))
        accepted = True
        yield from lines

    with patch.object(
        black.linegen, "_batch_split_flat_subscript_chain", side_effect=tracked
    ):
        candidate = black.format_str(source, mode=mode)
    with patch.object(
        black.linegen,
        "_batch_split_flat_subscript_chain",
        side_effect=black.linegen.CannotSplit("force legacy RHS splitting"),
    ):
        legacy = black.format_str(source, mode=mode)
    return accepted, candidate == legacy, digest(candidate), digest(legacy)


def main() -> int:
    cases: list[tuple[str, str, Mode]] = []
    for line_length in LINE_LENGTHS:
        for body_name, body in BODY_FACTORIES.items():
            for assignment_name, assignment in ASSIGNMENTS.items():
                source = (
                    assignment
                    + "a"
                    + "".join(f"[{body(index)}]" for index in range(60))
                    + "\n"
                )
                cases.append((
                    f"ll={line_length}/{body_name}/{assignment_name}",
                    source,
                    Mode(line_length=line_length),
                ))
    for assignment_name in ("top-level", "annotated"):
        source = (
            ASSIGNMENTS[assignment_name]
            + "a"
            + "".join(f"[key{index % 7}]" for index in range(60))
            + "\n"
        )
        cases.append((f"default/{assignment_name}", source, Mode()))

    mismatches: list[dict[str, str]] = []
    accepted_count = 0
    for case_id, source, mode in cases:
        accepted, identical, candidate_sha, legacy_sha = compare(source, mode)
        accepted_count += int(accepted)
        if not identical:
            mismatches.append({
                "case_id": case_id,
                "candidate_sha256": candidate_sha,
                "legacy_sha256": legacy_sha,
            })

    result = {
        "schema_version": 1,
        "case_count": len(cases),
        "batch_accepted_case_count": accepted_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "pass": not mismatches,
    }
    print(json.dumps(result, sort_keys=True))
    return int(bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
