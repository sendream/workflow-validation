#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import markdown_table as md
import workflow_routing as wr


PLACEHOLDERS = ("待填写", "TODO", "TBD", "optional /", "disabled / trial / available / required")
RISK_TIERS = ("low", "standard", "high", "release")
RUNNABLE_STATUS = {"available", "required"}
TRIAL_STATUS = {"trial"}
RUN_DISABLED_TOOL_CLASSES = {"graphify", "graph-code-index", "codegraph-index"}
APPROVAL_WRITE_SCOPES = {"repo-write", "external-write"}
APPROVAL_NETWORKS = {"internet", "remote"}
APPROVAL_SANDBOXES = {"ci", "remote"}
SHELL_PROGRAMS = {"sh", "bash", "dash", "zsh", "ksh"}
ARGV_LAUNCHER_PROGRAMS = SHELL_PROGRAMS | {"env"}
TOOL_REGISTRY_REQUIRED_COLUMNS = {"tool class", "tool", "status", "command", "blocking policy"}
INLINE_EVAL_FLAGS = {
    "node": {"-e", "--eval", "-p", "--print"},
    "perl": {"-e"},
    "php": {"-r", "-B", "-R", "-E"},
    "ruby": {"-e"},
}

TOOL_NAME_TO_CLASS = {
    "ast-grep": "semantic-search",
    "sg": "semantic-search",
    "gitleaks": "secret-scan",
    "semgrep": "sast",
    "codeql": "sast",
    "dependency-check": "dependency-scan",
    "owasp dependency-check": "dependency-scan",
    "openrewrite": "modernization",
    "rewrite": "modernization",
    "repomix": "context-pack",
    "markitdown": "document-convert",
    "markitdown-convert": "document-convert",
    "document-convert": "document-convert",
    "document-ingestion": "document-convert",
    "graphify": "graphify",
    # Legacy registry name retained for migrated projects. New tooling-map rows
    # must use graph-code-query for read-only lookup or graph-code-index for
    # refresh/index/watch actions.
    "graph-code-map": "graph-code-query",
    "graph-code-query": "graph-code-query",
    "structural-index": "graph-code-query",
    "structural index": "graph-code-query",
    "codegraph": "graph-code-query",
    "codegraph-query": "graph-code-query",
    "graph-code-index": "graph-code-index",
    "codegraph-index": "graph-code-index",
    "codegraph-watch": "graph-code-index",
    "pre-commit": "git-hooks",
    "lefthook": "git-hooks",
    "renovate": "dependency-update",
}

INFER_RULES = (
    (
        "secret-scan",
        ("密钥", "secret", "credential", "token", "api key", "配置", "部署", "env", "ci"),
    ),
    (
        "sast",
        ("权限", "认证", "安全", "输入", "sql", "命令", "文件上传", "auth", "permission", "upload", "xss", "csrf"),
    ),
    (
        "dependency-scan",
        ("依赖", "dependency", "package", "npm", "maven", "gradle", "pip", "升级"),
    ),
    (
        "semantic-search",
        ("跨模块", "跨层", "重构", "批量", "影响面", "refactor", "migration", "rewrite"),
    ),
    (
        "modernization",
        ("java", "spring", "openrewrite", "现代化", "框架迁移"),
    ),
    (
        "context-pack",
        ("大范围", "全仓", "上下文", "handoff", "context", "repomix"),
    ),
)


@dataclass
class ToolEntry:
    tool_class: str
    tool: str
    status: str
    trigger: str
    command: str
    blocking_policy: str
    owner: str
    approval: str
    sandbox: str
    write_scope: str
    network: str
    notes: str


@dataclass
class SelectedTool:
    tool_class: str
    tool: str
    status: str
    blocking_policy: str
    command: str
    command_argv: list[str]
    command_error: str
    action: str
    reason: str
    approval: str
    sandbox: str
    write_scope: str
    network: str
    owner: str


@dataclass
class RunResult:
    tool_class: str
    tool: str
    blocking_policy: str
    status: str
    command: str
    command_argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    started_at: str
    ended_at: str
    artifacts: list[str]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def section(text: str, title: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(title)}\s*$([\s\S]*?)(?=^## |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def has_placeholder(value: str) -> bool:
    compact = value.strip()
    if not compact:
        return True
    return any(marker.lower() in compact.lower() for marker in PLACEHOLDERS)


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_status(value: str) -> str:
    token = normalize_token(value)
    if "/" in token or has_placeholder(token):
        return "disabled"
    return token


def normalize_policy(value: str) -> str:
    token = normalize_token(value)
    if "/" in token or has_placeholder(token):
        return "none"
    if token in {"block", "warn", "none"}:
        return token
    if "block" in token:
        return "block"
    if "warn" in token:
        return "warn"
    return "none"


def normalize_approval(value: str) -> str:
    token = normalize_token(value)
    if not token or has_placeholder(token):
        return "none"
    if token in {"none", "not-needed", "not needed", "no", "false"}:
        return "none"
    if token in {"required", "approval-required", "manual", "yes", "true"}:
        return "required"
    if "approval" in token or "required" in token:
        return "required"
    return token


def defaulted(value: str, fallback: str) -> str:
    token = value.strip()
    if not token or has_placeholder(token):
        return fallback
    return token


def parse_risk_tier(task_plan: str) -> str:
    return wr.extract_risk_tier(task_plan) or "standard"


def parse_verification_matrix(task_plan: str) -> list[dict[str, str]]:
    matrix = section(task_plan, "Verification Matrix")
    rows_out: list[dict[str, str]] = []
    for table in md.parse_markdown_tables(matrix, strict=True):
        keys = [normalize_token(cell) for cell in table.headers]
        if not any("tool" in key or "工具" in key for key in keys):
            continue
        for row in table.rows:
            values = row + [""] * (len(keys) - len(row))
            rows_out.append({keys[index]: values[index] for index in range(len(keys))})
    return rows_out


def is_python_program(program: str) -> bool:
    return bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", program.lower()))


def is_inline_interpreter(program: str) -> bool:
    return is_python_program(program) or program.lower() in INLINE_EVAL_FLAGS


def inline_eval_flags(program: str) -> set[str]:
    if is_python_program(program):
        return {"-c"}
    return INLINE_EVAL_FLAGS.get(program.lower(), set())


def parse_tool_registry_tables(registry_text: str) -> list[md.MarkdownTable]:
    """Parse Tool Registry tables strictly; malformed safety config must fail closed."""
    tables: list[md.MarkdownTable] = []
    lines = registry_text.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("|"):
            index += 1
            continue

        start_line = index + 1
        table_lines: list[tuple[int, str]] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            table_lines.append((index + 1, lines[index].strip()))
            index += 1

        if len(table_lines) < 2:
            raise md.MarkdownTableError("Tool Registry table missing separator", line=start_line)

        header = md.split_markdown_table_row(table_lines[0][1])
        separator = md.split_markdown_table_row(table_lines[1][1])
        if not md.is_separator_row(separator):
            raise md.MarkdownTableError("Tool Registry table separator row invalid", line=table_lines[1][0])
        if len(separator) != len(header):
            raise md.MarkdownTableError("Tool Registry table separator column count mismatch", line=table_lines[1][0])

        rows: list[list[str]] = []
        for line_number, row_text in table_lines[2:]:
            row = md.split_markdown_table_row(row_text)
            if len(row) != len(header):
                raise md.MarkdownTableError("Tool Registry table row column count mismatch", line=line_number)
            rows.append(row)
        tables.append(md.MarkdownTable(headers=header, rows=rows, start_line=start_line, end_line=table_lines[-1][0]))

    return tables


def parse_tool_registry(tooling_map: str) -> list[ToolEntry]:
    entries: list[ToolEntry] = []
    registry_text = section(tooling_map, "Tool Registry") or tooling_map
    for table in parse_tool_registry_tables(registry_text):
        keys = [normalize_token(cell) for cell in table.headers]
        missing_columns = sorted(TOOL_REGISTRY_REQUIRED_COLUMNS - set(keys))
        if missing_columns:
            raise md.MarkdownTableError(
                "Tool Registry table missing required columns: " + ", ".join(missing_columns),
                line=table.start_line,
            )

        def cell(row: list[str], *names: str) -> str:
            idx = -1
            for name in names:
                if name in keys:
                    idx = keys.index(name)
                    break
            if idx < 0:
                return ""
            return row[idx] if idx < len(row) else ""

        for row in table.rows:
            if not row or all(not cell.strip() for cell in row):
                continue
            entries.append(
                ToolEntry(
                    tool_class=normalize_token(cell(row, "tool class")),
                    tool=cell(row, "tool").strip(),
                    status=normalize_status(cell(row, "status")),
                    trigger=cell(row, "trigger").strip(),
                    command=cell(row, "command").strip(),
                    blocking_policy=normalize_policy(cell(row, "blocking policy")),
                    owner=cell(row, "owner").strip(),
                    approval=normalize_approval(cell(row, "approval")),
                    sandbox=defaulted(cell(row, "sandbox"), "local"),
                    write_scope=defaulted(cell(row, "write scope", "write_scope"), "unspecified"),
                    network=defaulted(cell(row, "network"), "project-default"),
                    notes=cell(row, "notes").strip(),
                )
            )
    return entries


def split_tooling_cell(value: str) -> set[str]:
    normalized = normalize_token(value)
    if not normalized or normalized in {"none", "无", "n/a", "-"}:
        return set()
    parts = re.split(r"[,，/、;；\n]+", normalized)
    classes: set[str] = set()
    for raw in parts:
        token = raw.strip(" `")
        if not token or token in {"none", "无", "待填写"}:
            continue
        classes.add(TOOL_NAME_TO_CLASS.get(token, token))
    return classes


def keyword_matches(text: str, keyword: str) -> bool:
    token = keyword.lower()
    if re.fullmatch(r"[a-z0-9_+-]+", token):
        return re.search(rf"(?<![a-z0-9_+-]){re.escape(token)}(?![a-z0-9_+-])", text) is not None
    return token in text


def infer_tool_classes(rows: list[dict[str, str]], risk_tier: str) -> set[str]:
    if risk_tier not in {"high", "release"}:
        return set()

    combined = " ".join(" ".join(row.values()) for row in rows).lower()
    classes: set[str] = set()
    for tool_class, keywords in INFER_RULES:
        if any(keyword_matches(combined, keyword) for keyword in keywords):
            classes.add(tool_class)
    if risk_tier == "release":
        classes.update({"secret-scan", "dependency-scan"})
    return classes


def required_tool_classes(rows: list[dict[str, str]], risk_tier: str) -> set[str]:
    classes: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if "tool" in key or "工具" in key:
                classes.update(split_tooling_cell(value))
    classes.update(infer_tool_classes(rows, risk_tier))
    return {item for item in classes if item and item != "none"}


def command_ready(command: str) -> bool:
    return not has_placeholder(command)


def parse_command_argv(command: str) -> tuple[list[str], str | None]:
    """Parse a tooling-map command as a single argv command, not a shell script."""
    if has_placeholder(command):
        return [], "placeholder-command"
    if "\n" in command or "\r" in command:
        return [], "newline-in-command"
    if "$(" in command or "`" in command:
        return [], "command-substitution"
    if re.search(r"(^|[^&])&&([^&]|$)|\|\|", command):
        return [], "command-chaining"
    if re.search(r"[;|<>]", command):
        return [], "shell-metacharacter"
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return [], "parse-error"
    if not argv:
        return [], "empty-command"
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[0]):
        return [], "env-assignment"
    program = Path(argv[0]).name
    if program in SHELL_PROGRAMS:
        return [], "shell-reentry"
    if any(Path(token).name in ARGV_LAUNCHER_PROGRAMS for token in argv[1:]):
        return [], "shell-reentry"
    if program == "env":
        env_command = first_env_command(argv[1:])
        if env_command and Path(env_command).name in SHELL_PROGRAMS:
            return [], "shell-reentry"
        return [], "env-assignment"
    if inline_eval_reentry(argv):
        return [], "inline-eval"
    return argv, None


def inline_eval_reentry(argv: list[str]) -> bool:
    for index, token in enumerate(argv):
        program = Path(token).name
        flags = inline_eval_flags(program)
        if not flags:
            continue
        if any(arg in flags for arg in argv[index + 1 :]):
            return True
    return False


def first_env_command(args: list[str]) -> str:
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            break
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
            index += 1
            continue
        if token in {"-i", "-0"}:
            index += 1
            continue
        if token in {"-u", "-C", "-S"}:
            if token == "-S" and index + 1 < len(args):
                try:
                    split_args = shlex.split(args[index + 1], posix=True)
                except ValueError:
                    return args[index + 1]
                return first_env_command(split_args)
            index += 2
            continue
        if token.startswith("--ignore-environment") or token.startswith("--null"):
            index += 1
            continue
        if token.startswith("--unset=") or token.startswith("--chdir=") or token.startswith("--split-string="):
            if token.startswith("--split-string="):
                try:
                    split_args = shlex.split(token.split("=", 1)[1], posix=True)
                except ValueError:
                    return token.split("=", 1)[1]
                return first_env_command(split_args)
            index += 1
            continue
        if token.startswith("-"):
            return token
        break
    return args[index] if index < len(args) else ""


def command_contract_error(command: str) -> str | None:
    _argv, error = parse_command_argv(command)
    return error


def approval_needed(entry: ToolEntry, approved: bool) -> bool:
    return entry_requires_approval(entry) and not approved


def cell_has_any(value: str, expected: set[str]) -> bool:
    normalized = normalize_token(value)
    tokens = {token.strip() for token in re.split(r"[/,，、;；\s]+", normalized) if token.strip()}
    return bool(tokens & expected)


def entry_requires_approval(entry: ToolEntry) -> bool:
    if entry.approval == "required":
        return True
    return (
        cell_has_any(entry.write_scope, APPROVAL_WRITE_SCOPES)
        or cell_has_any(entry.network, APPROVAL_NETWORKS)
        or cell_has_any(entry.sandbox, APPROVAL_SANDBOXES)
    )


def graph_code_query_policy_issue(entry: ToolEntry) -> str | None:
    if entry.tool_class != "graph-code-query":
        return None
    if not cell_has_any(entry.write_scope, {"read-only"}):
        return "graph-code-query must have Write scope=read-only"
    if cell_has_any(entry.network, {"internet", "remote"}):
        return "graph-code-query must not use internet or remote network"
    command_lower = normalize_token(entry.command)
    if re.search(r"(\binit\s+-i\b|\bindex\b|\bwatch\b|\bsync\b|\.codegraph|codegraph-out)", command_lower):
        return "graph-code-query command must not index, watch, sync, or write CodeGraph cache paths"
    return None


def approval_misconfigured(entry: ToolEntry) -> bool:
    return entry.status in (RUNNABLE_STATUS | TRIAL_STATUS) and entry_requires_approval(entry) and entry.approval != "required"


def select_tools(
    entries: list[ToolEntry],
    needed_classes: set[str],
    include_trial: bool,
    approved: bool,
) -> list[SelectedTool]:
    selected: list[SelectedTool] = []
    for entry in entries:
        if entry.tool_class not in needed_classes:
            continue
        command_argv, command_error = parse_command_argv(entry.command)
        query_policy_issue = graph_code_query_policy_issue(entry) if entry.status in (RUNNABLE_STATUS | TRIAL_STATUS) else None
        if query_policy_issue:
            action = "configure"
            reason = "graph-code-query-policy-invalid"
        elif entry.tool_class not in RUN_DISABLED_TOOL_CLASSES and approval_misconfigured(entry):
            action = "configure"
            reason = "approval-policy-invalid"
        elif entry.tool_class in RUN_DISABLED_TOOL_CLASSES:
            action = "skip"
            tool_name = str(entry.tool).lower()
            if "codegraph" in tool_name or entry.tool_class in {"graph-code-index", "codegraph-index"}:
                reason = "codegraph-run-disabled"
            else:
                reason = f"{entry.tool_class}-run-disabled"
        elif entry.status in RUNNABLE_STATUS:
            if not command_ready(entry.command):
                action = "configure"
                reason = "command-not-configured"
            elif command_error:
                action = "configure"
                reason = "unsafe-command"
            elif approval_needed(entry, approved):
                action = "approval-required"
                reason = "approval-required" if entry.approval == "required" else "policy-approval-required"
            else:
                action = "run"
                reason = "matched-required-class"
        elif entry.status in TRIAL_STATUS and include_trial:
            if not command_ready(entry.command):
                action = "configure"
                reason = "command-not-configured"
            elif command_error:
                action = "configure"
                reason = "unsafe-command"
            elif approval_needed(entry, approved):
                action = "approval-required"
                reason = "approval-required" if entry.approval == "required" else "policy-approval-required"
            else:
                action = "run"
                reason = "matched-trial-class"
        elif entry.status in TRIAL_STATUS:
            action = "skip"
            reason = "trial-not-included"
        else:
            action = "skip"
            reason = f"status-{entry.status}"
        selected.append(
            SelectedTool(
                tool_class=entry.tool_class,
                tool=entry.tool,
                status=entry.status,
                blocking_policy=entry.blocking_policy,
                command=entry.command,
                command_argv=command_argv,
                command_error=command_error or "",
                action=action,
                reason=reason,
                approval=entry.approval,
                sandbox=entry.sandbox,
                write_scope=entry.write_scope,
                network=entry.network,
                owner=entry.owner,
            )
        )
    return selected


def validate_entries(entries: list[ToolEntry]) -> list[str]:
    issues: list[str] = []
    for entry in entries:
        label = f"{entry.tool_class}/{entry.tool}"
        if approval_misconfigured(entry):
            issues.append(
                f"{label}: Approval must be required for repo-write, external-write, internet, remote, or ci tools"
            )
        query_policy_issue = graph_code_query_policy_issue(entry) if entry.status in (RUNNABLE_STATUS | TRIAL_STATUS) else None
        if query_policy_issue:
            issues.append(f"{label}: {query_policy_issue}")
        must_be_ready = entry.status == "required" or entry.blocking_policy == "block"
        if not must_be_ready:
            if entry.status in (RUNNABLE_STATUS | TRIAL_STATUS) and command_ready(entry.command):
                command_error = command_contract_error(entry.command)
                if command_error:
                    issues.append(f"{label}: command contract invalid ({command_error})")
            continue
        if has_placeholder(entry.owner):
            issues.append(f"{label}: owner is required for required/block tools")
        if not command_ready(entry.command):
            issues.append(f"{label}: command is required for required/block tools")
        else:
            command_error = command_contract_error(entry.command)
            if command_error:
                issues.append(f"{label}: command contract invalid ({command_error})")
        if entry.blocking_policy == "block" and entry.status not in RUNNABLE_STATUS:
            issues.append(f"{label}: block tools must be available or required")
        if entry.approval == "required" and has_placeholder(entry.owner):
            issues.append(f"{label}: approval-required tools must have an owner")
    return issues


def missing_required_tool_classes(entries: list[ToolEntry], needed_classes: set[str]) -> list[str]:
    registered_classes = {entry.tool_class for entry in entries if entry.tool_class}
    missing = sorted(needed_classes - registered_classes)
    return [f"{tool_class}: required tool class has no Tool Registry row" for tool_class in missing]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_timestamp(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def milliseconds_between(start: str, end: str) -> int | None:
    started = parse_utc_timestamp(start)
    ended = parse_utc_timestamp(end)
    if started is None or ended is None:
        return None
    return max(0, int((ended - started).total_seconds() * 1000))


def generated_id(prefix: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "unnamed"


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_state_root(root: Path) -> Path:
    return root / ".agent-state" / "runs"


def write_run_manifest(
    root: Path,
    artifact_dir: Path,
    payload: dict[str, Any],
    artifacts: list[str],
) -> str:
    results = payload.get("results") or []
    stdout_paths: list[str] = []
    stderr_paths: list[str] = []
    commands: list[str] = []
    command_argvs: list[list[str]] = []
    result_starts: list[str] = []
    result_ends: list[str] = []
    tool_runtime_ms = 0
    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            command = result.get("command")
            if isinstance(command, str) and command:
                commands.append(command)
            command_argv = result.get("command_argv")
            if isinstance(command_argv, list) and all(isinstance(part, str) for part in command_argv):
                command_argvs.append(command_argv)
            started_at = result.get("started_at")
            ended_at = result.get("ended_at")
            if isinstance(started_at, str) and started_at:
                result_starts.append(started_at)
            if isinstance(ended_at, str) and ended_at:
                result_ends.append(ended_at)
            if isinstance(started_at, str) and isinstance(ended_at, str):
                elapsed = milliseconds_between(started_at, ended_at)
                if elapsed is not None:
                    tool_runtime_ms += elapsed
            result_artifacts = result.get("artifacts")
            if isinstance(result_artifacts, list):
                for artifact in result_artifacts:
                    if not isinstance(artifact, str):
                        continue
                    if artifact.endswith(".stdout.log"):
                        stdout_paths.append(artifact)
                    if artifact.endswith(".stderr.log"):
                        stderr_paths.append(artifact)

    payload_artifact = payload.get("artifact")
    artifact_sha256 = "not-needed"
    if isinstance(payload_artifact, str) and payload_artifact:
        artifact_path = root / payload_artifact
        if artifact_path.is_file():
            artifact_sha256 = file_sha256(artifact_path)

    created_at = utc_now()
    started_at = min(result_starts) if result_starts else created_at
    completed_at = max(result_ends) if result_ends else created_at
    duration_ms = milliseconds_between(started_at, completed_at)
    if duration_ms is None:
        duration_ms = tool_runtime_ms
    run_blockers = payload.get("run_blockers") or []
    blocked_reason = str(run_blockers[0]) if isinstance(run_blockers, list) and run_blockers else "not-needed"
    manifest = {
        "schema_version": 1,
        "ids": payload.get("ids", {}),
        "risk_tier": payload.get("risk_tier", "unknown"),
        "tool": "tooling-router",
        "command": commands[0] if len(commands) == 1 else "tooling-router",
        "commands": commands,
        "command_argvs": command_argvs,
        "status": "passed" if payload.get("exit_code") == 0 else "failed",
        "exit_code": payload.get("exit_code"),
        "stdout_path": stdout_paths[0] if stdout_paths else "not-needed",
        "stderr_path": stderr_paths[0] if stderr_paths else "not-needed",
        "stdout_paths": stdout_paths,
        "stderr_paths": stderr_paths,
        "summary": f"tooling-router selected {len(payload.get('selected', []))} tool(s); ran {len(results)} tool(s)",
        "sha256": artifact_sha256,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "tool_runtime_ms": tool_runtime_ms,
        "blocked_reason": blocked_reason,
        "redaction_status": "unknown",
        "token_usage": {"status": "unavailable", "input_tokens": None, "output_tokens": None, "total_tokens": None},
        "estimated_cost": {"status": "unavailable", "currency": "USD", "amount": None},
        "external_lookup_ledger": [],
        "needed_classes": payload.get("needed_classes", []),
        "approval_required": payload.get("approval_required", []),
        "approval_required_count": len(payload.get("approval_required", [])),
        "validation_issues": payload.get("validation_issues", []),
        "run_blockers": run_blockers,
        "artifacts": artifacts,
    }
    manifest_path = artifact_dir / "manifest.json"
    write_artifact(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return relative_to_root(root, manifest_path)


def run_selected(
    root: Path,
    selected: list[SelectedTool],
    timeout: int,
    artifact_dir: Path | None,
) -> tuple[list[RunResult], int]:
    results: list[RunResult] = []
    exit_code = 0
    for item in selected:
        if item.action != "run":
            continue
        started_at = utc_now()
        try:
            completed = subprocess.run(
                item.command_argv,
                cwd=root,
                shell=False,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
            returncode = 124
        ended_at = utc_now()

        status = "passed" if returncode == 0 else "failed"
        if returncode != 0 and item.blocking_policy == "block":
            exit_code = 2
        artifacts: list[str] = []
        if artifact_dir is not None:
            prefix = safe_slug(f"{item.tool_class}-{item.tool}")
            stdout_path = artifact_dir / f"{prefix}.stdout.log"
            stderr_path = artifact_dir / f"{prefix}.stderr.log"
            write_artifact(stdout_path, stdout)
            write_artifact(stderr_path, stderr)
            artifacts.extend([relative_to_root(root, stdout_path), relative_to_root(root, stderr_path)])
        results.append(
            RunResult(
                tool_class=item.tool_class,
                tool=item.tool,
                blocking_policy=item.blocking_policy,
                status=status,
                command=item.command,
                command_argv=item.command_argv,
                returncode=returncode,
                stdout=stdout[:4000],
                stderr=stderr[:4000],
                started_at=started_at,
                ended_at=ended_at,
                artifacts=artifacts,
            )
        )
    return results, exit_code


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def disable_run_only_tools(selected: list[dict[str, Any]]) -> None:
    for item in selected:
        if item.get("action") != "run":
            continue
        if item.get("tool_class") in RUN_DISABLED_TOOL_CLASSES:
            item["action"] = "skip"
            tool_name = str(item.get("tool", "")).lower()
            if "codegraph" in tool_name or item.get("tool_class") in {"graph-code-index", "codegraph-index"}:
                item["reason"] = "codegraph-run-disabled"
            else:
                item["reason"] = f"{item['tool_class']}-run-disabled"


def selected_run_blockers(selected: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for item in selected:
        tool_class = str(item.get("tool_class", ""))
        if tool_class in RUN_DISABLED_TOOL_CLASSES:
            continue
        action = str(item.get("action", ""))
        status = str(item.get("status", ""))
        blocking_policy = str(item.get("blocking_policy", ""))
        must_produce_evidence = status == "required" or blocking_policy == "block"
        if not must_produce_evidence:
            continue
        label = f"{tool_class}/{item.get('tool', '')}"
        if action == "configure":
            blockers.append(f"{label}: selected required/block tool is not configured ({item.get('reason', 'configure')})")
        elif action == "skip":
            blockers.append(f"{label}: selected required/block tool was skipped ({item.get('reason', 'skip')})")
    return blockers


def extract_ids(task_plan: str, run_id_arg: str | None, trace_id_arg: str | None) -> dict[str, str]:
    def value(label: str) -> str:
        pattern = re.compile(rf"(?mi)^\s*[-*]?\s*{re.escape(label)}\s*[:：]\s*(.+?)\s*$")
        match = pattern.search(task_plan)
        if not match:
            return ""
        raw = match.group(1).strip()
        return "" if has_placeholder(raw) or raw.lower() in {"optional", "none"} else raw

    task_id = value("Task ID") or value("task_id") or generated_id("task")
    run_id = run_id_arg or value("Run ID") or value("run_id") or generated_id("run")
    trace_id = trace_id_arg or value("Trace ID") or value("trace_id") or generated_id("trace")
    return {"task_id": task_id, "run_id": run_id, "trace_id": trace_id}


def build_payload(root: Path, include_trial: bool, approved: bool, run_id: str | None, trace_id: str | None) -> dict[str, Any]:
    task_plan = read_text(root / "task_plan.md")
    tooling_map = read_text(root / ".agents" / "references" / "tooling-map.md")
    risk_tier = parse_risk_tier(task_plan)
    validation_issues: list[str] = []
    parse_errors: list[str] = []
    try:
        matrix_rows = parse_verification_matrix(task_plan)
    except md.MarkdownTableError as exc:
        matrix_rows = []
        parse_errors.append(f"task_plan.md Verification Matrix: {exc}")
    needed_classes = required_tool_classes(matrix_rows, risk_tier)
    try:
        entries = parse_tool_registry(tooling_map)
    except md.MarkdownTableError as exc:
        entries = []
        parse_errors.append(f".agents/references/tooling-map.md Tool Registry: {exc}")
    selected = select_tools(entries, needed_classes, include_trial, approved)
    selection_errors = missing_required_tool_classes(entries, needed_classes)
    validation_issues.extend(parse_errors)
    validation_issues.extend(selection_errors)
    validation_issues.extend(validate_entries(entries))
    return {
        "ids": extract_ids(task_plan, run_id, trace_id),
        "risk_tier": risk_tier,
        "needed_classes": sorted(needed_classes),
        "selected": [asdict(item) for item in selected],
        "approval_required": [asdict(item) for item in selected if item.action == "approval-required"],
        "parse_errors": parse_errors,
        "selection_errors": selection_errors,
        "validation_issues": validation_issues,
    }


def emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    print(f"Risk Tier: {payload.get('risk_tier', 'unknown')}")
    print("Needed classes: " + ", ".join(payload.get("needed_classes", [])))
    if payload.get("validation_issues"):
        print("Validation issues:")
        for issue in payload["validation_issues"]:
            print(f"- {issue}")
    if payload.get("selected"):
        print("Selected tools:")
        for item in payload["selected"]:
            print(
                f"- {item['tool_class']} / {item['tool']}: "
                f"{item['action']} ({item['blocking_policy']}, {item['reason']})"
            )
    if payload.get("approval_required"):
        print("Approval required:")
        for item in payload["approval_required"]:
            print(f"- {item['tool_class']} / {item['tool']}: owner={item.get('owner', 'unknown')}")
    if payload.get("results"):
        print("Run results:")
        for item in payload["results"]:
            print(f"- {item['tool']}: {item['status']} ({item['returncode']})")
    if payload.get("artifact"):
        print(f"Artifact: {payload['artifact']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route project tooling checks from task_plan.md and tooling-map.md.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--mode", choices=("plan", "run", "validate"), default="plan")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--include-trial", action="store_true", help="Allow trial tools to run when selected.")
    parser.add_argument("--approved", action="store_true", help="Allow tools whose registry row requires explicit approval.")
    parser.add_argument("--run-id", help="Override run_id for artifact paths and payload metadata.")
    parser.add_argument("--trace-id", help="Override trace_id for payload metadata.")
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Do not write .agent-state/runs/<run_id>/tooling-router-result.json in run mode.",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Per-tool timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    payload = build_payload(
        root,
        include_trial=args.include_trial,
        approved=args.approved,
        run_id=args.run_id,
        trace_id=args.trace_id,
    )

    if args.mode == "validate":
        payload["exit_code"] = 2 if payload["validation_issues"] else 0
        emit(payload, args.format)
        return int(payload["exit_code"])

    if args.mode == "run":
        disable_run_only_tools(payload["selected"])
        payload["run_blockers"] = selected_run_blockers(payload["selected"])
        if payload["parse_errors"]:
            payload["run_blockers"].extend(f"parse: {issue}" for issue in payload["parse_errors"])
        if payload.get("selection_errors"):
            payload["run_blockers"].extend(f"selection: {issue}" for issue in payload["selection_errors"])

        artifact_dir = None
        if not args.no_artifacts:
            artifact_dir = run_state_root(root) / safe_slug(payload["ids"]["run_id"])
            artifact_dir.mkdir(parents=True, exist_ok=True)

        if payload["approval_required"]:
            payload["exit_code"] = 3
            if artifact_dir is not None:
                artifact = artifact_dir / "tooling-router-result.json"
                payload["artifact"] = relative_to_root(root, artifact)
                write_artifact(artifact, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                payload["run_manifest"] = write_run_manifest(
                    root,
                    artifact_dir,
                    payload,
                    [payload["artifact"]],
                )
            emit(payload, args.format)
            return 3

        if payload["run_blockers"]:
            payload["exit_code"] = 4
            if artifact_dir is not None:
                artifact = artifact_dir / "tooling-router-result.json"
                payload["artifact"] = relative_to_root(root, artifact)
                write_artifact(artifact, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                payload["run_manifest"] = write_run_manifest(
                    root,
                    artifact_dir,
                    payload,
                    [payload["artifact"]],
                )
            emit(payload, args.format)
            return 4

        selected = [
            SelectedTool(
                tool_class=item["tool_class"],
                tool=item["tool"],
                status=item["status"],
                blocking_policy=item["blocking_policy"],
                command=item["command"],
                command_argv=item.get("command_argv", []),
                command_error=item.get("command_error", ""),
                action=item["action"],
                reason=item["reason"],
                approval=item["approval"],
                sandbox=item["sandbox"],
                write_scope=item["write_scope"],
                network=item["network"],
                owner=item["owner"],
            )
            for item in payload["selected"]
        ]
        results, exit_code = run_selected(root, selected, args.timeout, artifact_dir)
        payload["results"] = [asdict(item) for item in results]
        payload["exit_code"] = exit_code
        if artifact_dir is not None:
            artifact = artifact_dir / "tooling-router-result.json"
            payload["artifact"] = relative_to_root(root, artifact)
            write_artifact(artifact, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            artifacts = [payload["artifact"]]
            for result in results:
                artifacts.extend(result.artifacts)
            payload["run_manifest"] = write_run_manifest(root, artifact_dir, payload, artifacts)
        emit(payload, args.format)
        return exit_code

    payload["exit_code"] = 0
    emit(payload, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
