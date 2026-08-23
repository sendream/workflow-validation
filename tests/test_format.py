import re
from collections.abc import Iterator
from dataclasses import replace
from typing import Any
from unittest.mock import patch

import pytest

import black
import black.linegen
from black.mode import TargetVersion
from tests.util import (
    all_data_cases,
    assert_format,
    dump_to_stderr,
    read_data,
    read_data_with_mode,
)


@pytest.fixture(autouse=True)
def patch_dump_to_file(request: Any) -> Iterator[None]:
    with patch("black.dump_to_file", dump_to_stderr):
        yield


def check_file(subdir: str, filename: str, *, data: bool = True) -> None:
    args, source, expected = read_data_with_mode(subdir, filename, data=data)
    assert_format(
        source,
        expected,
        args.mode,
        fast=args.fast,
        minimum_version=args.minimum_version,
        lines=args.lines,
        no_preview_line_length_1=args.no_preview_line_length_1,
    )
    if args.minimum_version is not None:
        major, minor = args.minimum_version
        target_version = TargetVersion[f"PY{major}{minor}"]
        mode = replace(args.mode, target_versions={target_version})
        assert_format(
            source,
            expected,
            mode,
            fast=args.fast,
            minimum_version=args.minimum_version,
            lines=args.lines,
            no_preview_line_length_1=args.no_preview_line_length_1,
        )


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
@pytest.mark.parametrize("filename", all_data_cases("cases"))
def test_simple_format(filename: str) -> None:
    check_file("cases", filename)


@pytest.mark.parametrize("filename", all_data_cases("line_ranges_formatted"))
def test_line_ranges_line_by_line(filename: str) -> None:
    args, source, expected = read_data_with_mode("line_ranges_formatted", filename)
    assert (
        source == expected
    ), "Test cases in line_ranges_formatted must already be formatted."
    line_count = len(source.splitlines())
    for line in range(1, line_count + 1):
        assert_format(
            source,
            expected,
            args.mode,
            fast=args.fast,
            minimum_version=args.minimum_version,
            lines=[(line, line)],
        )


# =============== #
# Unusual cases
# =============== #


def test_empty() -> None:
    source = expected = ""
    assert_format(source, expected)


def test_long_flat_subscript_chain_split_work_is_linear() -> None:
    small_source, expected = read_data("cases", "long_flat_subscript_chain")
    large_source = "x = a" + "".join(f"[{i}]" for i in range(160)) + "\n"

    with patch.object(
        black.linegen,
        "_first_right_hand_split",
        wraps=black.linegen._first_right_hand_split,
    ) as small_split:
        actual = black.format_str(small_source, mode=black.Mode())

    with patch.object(
        black.linegen,
        "_first_right_hand_split",
        wraps=black.linegen._first_right_hand_split,
    ) as large_split:
        black.format_str(large_source, mode=black.Mode())

    assert actual == expected
    assert (
        small_split.call_count <= 2 * 80
    ), f"80 subscripts required {small_split.call_count} RHS split attempts"
    assert (
        large_split.call_count <= 2 * 160
    ), f"160 subscripts required {large_split.call_count} RHS split attempts"


@pytest.mark.parametrize(
    ("assignment", "body_pattern", "batch_expected"),
    [
        ("result = ", "names", True),
        ("result: list[int] = ", "names", True),
        ("result = ", "increasing-numbers", True),
        ("result = ", "nonmonotonic-numbers", False),
        ("result = ", "increasing-wide-strings", False),
    ],
)
def test_long_flat_subscript_chain_matches_legacy_split(
    assignment: str, body_pattern: str, batch_expected: bool
) -> None:
    if body_pattern == "names":
        bodies = [f"key{index % 7}" for index in range(60)]
    elif body_pattern == "increasing-numbers":
        bodies = [str(10 ** (index // 10) + index) for index in range(60)]
    elif body_pattern == "nonmonotonic-numbers":
        bodies = [
            str(10**15 + index) if index % 3 == 0 else str(index) for index in range(60)
        ]
    else:
        bodies = [repr("字" * (index // 5 + 1)) for index in range(30)]
    source = assignment + "a" + "".join(f"[{body}]" for body in bodies) + "\n"

    original = black.linegen._batch_split_flat_subscript_chain
    batch_accepted = False

    def tracked_batch(*args: Any, **kwargs: Any) -> Iterator[black.lines.Line]:
        nonlocal batch_accepted
        lines = list(original(*args, **kwargs))
        batch_accepted = True
        yield from lines

    with patch.object(
        black.linegen,
        "_batch_split_flat_subscript_chain",
        side_effect=tracked_batch,
    ):
        actual = black.format_str(source, mode=black.Mode())

    with patch.object(
        black.linegen,
        "_batch_split_flat_subscript_chain",
        side_effect=black.linegen.CannotSplit("force legacy RHS splitting"),
    ):
        legacy = black.format_str(source, mode=black.Mode())

    assert actual == legacy
    assert batch_accepted is batch_expected


def test_patma_invalid() -> None:
    source, expected = read_data("miscellaneous", "pattern_matching_invalid")
    mode = black.Mode(target_versions={black.TargetVersion.PY310})
    with pytest.raises(black.parsing.InvalidInput) as exc_info:
        assert_format(source, expected, mode, minimum_version=(3, 10))

    exc_info.match(
        re.escape(
            "cannot parse for target version Python 3.10: 10:11\n"
            "        case a := b:\n"
            "              ^\n"
            "ParseError: bad input"
        )
    )
