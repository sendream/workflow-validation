#!/usr/bin/env python3
"""Shared Markdown document boundaries for workflow validators."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import markdown_table as table_parser


@dataclass(frozen=True)
class MarkdownSection:
    heading: str
    level: int
    start_line: int
    end_line: int
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def normalize_heading(value: str) -> str:
    value = re.sub(r"^#{1,6}\s+", "", value.strip())
    return re.sub(r"\s+", " ", value).strip().lower()


def without_fenced_blocks(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    visible = table_parser.non_fenced_line_mask(lines)
    return "\n".join(line if visible[index] else "" for index, line in enumerate(lines))


def section(markdown_text: str, heading: str, *, occurrence: str = "first") -> MarkdownSection | None:
    if occurrence != "first":
        raise ValueError("only occurrence='first' is supported")
    wanted = normalize_heading(heading)
    requested = re.match(r"^(#{1,6})\s+", heading.strip())
    requested_level = len(requested.group(1)) if requested else None
    lines = markdown_text.splitlines()
    visible = table_parser.non_fenced_line_mask(lines)
    start_index: int | None = None
    level = 0
    title = ""
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if not match:
            continue
        current_level = len(match.group(1))
        current_title = match.group(2).strip()
        if start_index is None:
            if normalize_heading(current_title) == wanted and (requested_level is None or current_level == requested_level):
                start_index = index
                level = current_level
                title = current_title
            continue
        if current_level <= level:
            return MarkdownSection(title, level, start_index + 1, index, lines[start_index + 1 : index])
    if start_index is None:
        return None
    return MarkdownSection(title, level, start_index + 1, len(lines), lines[start_index + 1 :])


def section_text(markdown_text: str, heading: str) -> str:
    found = section(markdown_text, heading)
    return found.text if found else ""


def section_lines(markdown_text: str, heading: str) -> list[str]:
    found = section(markdown_text, heading)
    return list(found.lines) if found else []


def remove_section(markdown_text: str, heading: str) -> str:
    found = section(markdown_text, heading)
    if found is None:
        return markdown_text
    lines = markdown_text.splitlines()
    start = found.start_line - 1
    end = found.end_line
    return "\n".join(lines[:start] + lines[end:])


def _default_key(value: str) -> str:
    return table_parser.clean_cell(value).lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def table_dict_rows(
    source: MarkdownSection | str | None,
    *,
    strict: bool = False,
    normalize_key: Callable[[str], str] | None = None,
    legacy_pipe_rows: bool = False,
) -> list[dict[str, str]]:
    text = source.text if isinstance(source, MarkdownSection) else (source or "")
    key_fn = normalize_key or _default_key
    rows: list[dict[str, str]] = []
    for table in table_parser.parse_markdown_tables(text, strict=strict):
        headers = [key_fn(cell) for cell in table.headers]
        for cells in table.rows:
            if len(cells) != len(headers):
                if strict:
                    raise table_parser.MarkdownTableError("Markdown table row column count mismatch")
                continue
            rows.append(dict(zip(headers, cells)))
    if rows or not legacy_pipe_rows:
        return rows

    raw_lines = text.splitlines()
    visible = table_parser.non_fenced_line_mask(raw_lines)
    pipe_lines = [line.strip() for index, line in enumerate(raw_lines) if visible[index] and line.strip().startswith("|")]
    if len(pipe_lines) < 2:
        return rows
    headers = [key_fn(cell) for cell in table_parser.split_markdown_table_row(pipe_lines[0])]
    for line in pipe_lines[1:]:
        cells = table_parser.split_markdown_table_row(line)
        if table_parser.is_separator_row(cells):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def key_value_table(source: MarkdownSection | str | None, *, strict: bool = False) -> dict[str, str]:
    rows = table_dict_rows(
        source,
        strict=strict,
        normalize_key=lambda value: table_parser.clean_cell(value).lower(),
        legacy_pipe_rows=True,
    )
    values: dict[str, str] = {}
    for row in rows:
        cells = list(row.values())
        if len(cells) < 2:
            continue
        key, value = table_parser.clean_cell(cells[0]).lower(), cells[1]
        if key in {"item", "field", "check"}:
            continue
        values[key] = value
    return values
