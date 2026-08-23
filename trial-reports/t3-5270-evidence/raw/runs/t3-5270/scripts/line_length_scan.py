#!/usr/bin/env python3
from __future__ import annotations

import json
from collections.abc import Iterator
from unittest.mock import patch

import black
import black.linegen
from black.lines import Line
from black.mode import Mode


def compare(source: str, mode: Mode) -> tuple[bool, bool]:
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
    return accepted, candidate == legacy


def main() -> int:
    assignments = {
        "top": "result = ",
        "annotated": "result: list[int] = ",
        "chained": "holder = result = ",
        "indented": "if True:\n    result = ",
        "subscript-lhs": "result[0] = ",
        "tuple-lhs": "(left, right) = ",
        "long-lhs": "this_is_a_very_long_assignment_target_name = ",
    }
    body_sets = {
        "equal-name": ["k"] * 30,
        "equal-number": ["0"] * 30,
        "increasing-name": ["k" + "x" * (index // 5) for index in range(30)],
        "increasing-number": [str(10 ** (index // 5) + index) for index in range(30)],
    }
    details: dict[str, object] = {}
    mismatch_count = 0
    accepted_count = 0
    case_count = 0
    for assignment_name, assignment in assignments.items():
        for body_name, bodies in body_sets.items():
            accepted_lengths: list[int] = []
            mismatch_lengths: list[int] = []
            source = assignment + "a" + "".join(f"[{body}]" for body in bodies) + "\n"
            for line_length in range(1, 141):
                case_count += 1
                accepted, identical = compare(source, Mode(line_length=line_length))
                if accepted:
                    accepted_lengths.append(line_length)
                    accepted_count += 1
                if not identical:
                    mismatch_lengths.append(line_length)
                    mismatch_count += 1
            details[f"{assignment_name}/{body_name}"] = {
                "accepted_lengths": accepted_lengths,
                "mismatch_lengths": mismatch_lengths,
            }

    mutations: dict[str, str] = {
        "top/base/equal-name": "result = base" + "[k]" * 30 + "\n",
        "top/long-base/equal-name": "result = long_ascii_rhs_base_name"
        + "[k]" * 30
        + "\n",
        "top/cjk-base/equal-name": "result = 基" + "[k]" * 30 + "\n",
    }
    for multiplier in range(1, 7):
        cjk_name = "名" * (multiplier * 8)
        mutations[f"cjk-lhs-{multiplier}/equal-name"] = (
            cjk_name + " = a" + "[k]" * 30 + "\n"
        )
        mutations[f"cjk-annotation-{multiplier}/equal-name"] = (
            "result: " + cjk_name + " = base" + "[k]" * 30 + "\n"
        )
    for case_name, source in mutations.items():
        accepted_lengths = []
        mismatch_lengths = []
        for line_length in range(1, 141):
            case_count += 1
            accepted, identical = compare(source, Mode(line_length=line_length))
            if accepted:
                accepted_lengths.append(line_length)
                accepted_count += 1
            if not identical:
                mismatch_lengths.append(line_length)
                mismatch_count += 1
        details[case_name] = {
            "accepted_lengths": accepted_lengths,
            "mismatch_lengths": mismatch_lengths,
        }

    result = {
        "schema_version": 1,
        "line_lengths": [1, 140],
        "case_count": case_count,
        "batch_accepted_case_count": accepted_count,
        "mismatch_count": mismatch_count,
        "details": details,
        "pass": mismatch_count == 0,
    }
    print(json.dumps(result, sort_keys=True))
    return int(bool(mismatch_count))


if __name__ == "__main__":
    raise SystemExit(main())
