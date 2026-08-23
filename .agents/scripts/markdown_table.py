#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownTable:
    headers: list[str]
    rows: list[list[str]]
    start_line: int
    end_line: int


class MarkdownTableError(ValueError):
    def __init__(self, message: str, *, line: int | None = None) -> None:
        self.line = line
        suffix = f" at line {line}" if line is not None else ""
        super().__init__(f"{message}{suffix}")


def non_fenced_line_mask(lines: list[str]) -> list[bool]:
    visible: list[bool] = []
    fence_char = ""
    fence_length = 0
    for line in lines:
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence_char:
            visible.append(False)
            if re.fullmatch(rf" {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*", line):
                fence_char = ""
                fence_length = 0
            continue
        if match:
            fence_char = match.group(1)[0]
            fence_length = len(match.group(1))
            visible.append(False)
            continue
        visible.append(True)
    return visible


def clean_cell(value: str) -> str:
    value = value.strip()
    opening_ticks = len(value) - len(value.lstrip("`"))
    closing_ticks = len(value) - len(value.rstrip("`"))
    if opening_ticks and opening_ticks == closing_ticks and len(value) >= opening_ticks * 2:
        value = value[opening_ticks:-closing_ticks]
    return value.strip()


def split_markdown_table_row(row: str) -> list[str]:
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    code_delimiter_length = 0
    backtick_run = 0

    for char in stripped:
        if escaped:
            if char == "|":
                current.append("|")
            else:
                current.append("\\")
                current.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == "`":
            backtick_run += 1
            current.append(char)
            continue

        if backtick_run:
            if code_delimiter_length == 0:
                code_delimiter_length = backtick_run
            elif backtick_run == code_delimiter_length:
                code_delimiter_length = 0
            backtick_run = 0

        if char == "|" and code_delimiter_length == 0:
            cells.append(clean_cell("".join(current)))
            current = []
            continue

        current.append(char)

    if escaped:
        current.append("\\")
    cells.append(clean_cell("".join(current)))
    return cells


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_markdown_tables(text: str, *, strict: bool = False) -> list[MarkdownTable]:
    tables: list[MarkdownTable] = []
    lines = text.splitlines()
    visible = non_fenced_line_mask(lines)
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not visible[index] or not line.startswith("|"):
            index += 1
            continue

        start = index + 1
        table_lines: list[tuple[int, str]] = []
        while index < len(lines) and visible[index] and lines[index].strip().startswith("|"):
            table_lines.append((index + 1, lines[index].strip()))
            index += 1

        if len(table_lines) < 2:
            continue

        header = split_markdown_table_row(table_lines[0][1])
        separator = split_markdown_table_row(table_lines[1][1])
        if not is_separator_row(separator):
            if strict:
                raise MarkdownTableError("Markdown table separator is malformed", line=table_lines[1][0])
            continue
        if strict and len(separator) != len(header):
            raise MarkdownTableError("Markdown table separator column count mismatch", line=table_lines[1][0])

        rows: list[list[str]] = []
        for line_number, row_text in table_lines[2:]:
            row = split_markdown_table_row(row_text)
            if strict and len(row) != len(header):
                raise MarkdownTableError("Markdown table row column count mismatch", line=line_number)
            rows.append(row)
        tables.append(MarkdownTable(headers=header, rows=rows, start_line=start, end_line=table_lines[-1][0]))

    return tables
