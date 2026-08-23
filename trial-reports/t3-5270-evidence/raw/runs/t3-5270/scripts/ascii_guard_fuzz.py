#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterator
from unittest.mock import patch

import black
import black.linegen
from black.lines import Line
from black.mode import Mode


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compare(source: str, mode: Mode) -> tuple[bool, str, str]:
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
    return accepted, digest(candidate), digest(legacy)


def main() -> int:
    randomizer = random.Random(5270)
    assignments = (
        "result = ",
        "result: list[int] = ",
        "holder = result = ",
        "if True:\n    result = ",
        "result[0] = ",
        "(left, right) = ",
        "this_is_a_very_long_assignment_target_name = ",
    )
    mismatches: list[dict[str, object]] = []
    accepted_count = 0
    case_count = 400
    for case_index in range(case_count):
        count = randomizer.randint(24, 72)
        widths = sorted(randomizer.randint(1, 12) for _ in range(count))
        if randomizer.choice((True, False)):
            bodies = ["k" + "x" * width for width in widths]
            body_kind = "name"
        else:
            bodies = [str(10 ** (width - 1) + case_index) for width in widths]
            body_kind = "number"
        assignment = randomizer.choice(assignments)
        line_length = randomizer.randint(20, 140)
        source = assignment + "a" + "".join(f"[{body}]" for body in bodies) + "\n"
        accepted, candidate_sha, legacy_sha = compare(
            source, Mode(line_length=line_length)
        )
        accepted_count += int(accepted)
        if candidate_sha != legacy_sha:
            mismatches.append(
                {
                    "case_index": case_index,
                    "assignment": assignment,
                    "body_kind": body_kind,
                    "line_length": line_length,
                    "candidate_sha256": candidate_sha,
                    "legacy_sha256": legacy_sha,
                }
            )

    result = {
        "schema_version": 1,
        "seed": 5270,
        "case_count": case_count,
        "batch_accepted_case_count": accepted_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "pass": not mismatches,
    }
    print(json.dumps(result, sort_keys=True))
    return int(bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
