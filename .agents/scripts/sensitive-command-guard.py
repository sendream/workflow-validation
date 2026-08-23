#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import sensitive_guard_policy as policy


def load_payload(raw: str | None = None) -> Any:
    if raw is None:
        raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def find_commands(value: Any) -> list[str]:
    commands: list[str] = []

    def visit(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            for child_key, child_value in node.items():
                visit(child_value, str(child_key))
            return
        if isinstance(node, list):
            for child in node:
                visit(child, key)
            return
        if not isinstance(node, str):
            return

        lowered = key.lower()
        if lowered in {"command", "cmd", "shell_command", "script"}:
            commands.append(node)
        elif lowered in {"raw"} and any(token in node for token in ("sudo", ".env", ".ssh", "git push", "rm -rf")):
            commands.append(node)

    visit(value)
    return commands


def strict_enabled(root: Path, override: bool = False) -> bool:
    if override:
        return True
    return (
        (root / ".agent-state" / "flags" / "sensitive-guard-strict.enabled").exists()
        or (root / ".agents" / "state" / "sensitive-guard-strict.enabled").exists()
        or os.getenv("CODEX_SENSITIVE_GUARD_STRICT") == "1"
    )


def parse_invocation(argv: list[str]) -> tuple[Path, bool, Any | None]:
    root = Path.cwd()
    strict_override = False
    args = list(argv)
    command_args: list[str] | None = None

    parsed_root = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            command_args = args[index + 1 :]
            break
        if arg == "--strict":
            strict_override = True
            index += 1
            continue
        if arg == "--root":
            if index + 1 >= len(args):
                raise SystemExit("--root requires a path")
            root = Path(args[index + 1]).resolve()
            parsed_root = True
            index += 2
            continue
        if not parsed_root:
            # Backward-compatible hook mode: first positional argument is project root.
            root = Path(arg).resolve()
            parsed_root = True
            index += 1
            continue
        index += 1

    if command_args is not None:
        command = " ".join(command_args).strip()
        return root, strict_override, {"command": command} if command else {}

    return root, strict_override, None


def main(argv: list[str] | None = None) -> int:
    root, strict_override, explicit_payload = parse_invocation(sys.argv[1:] if argv is None else argv)
    payload = explicit_payload if explicit_payload is not None else load_payload()
    commands = find_commands(payload)
    if not commands:
        return 0

    hardline_rule_ids: set[str] = set()
    rule_ids: set[str] = set()
    for command in commands:
        hardline_rule_ids.update(policy.command_hardline_rule_ids(command))
        rule_ids.update(policy.command_rule_ids(command))

    if hardline_rule_ids:
        message = (
            "[sensitive-guard] hardline block：检测到不可覆盖的高危命令信号："
            + "、".join(policy.labels(hardline_rule_ids))
            + "。该类操作不能用普通确认、strict flag 关闭或交付压力绕过；请改用受控脚本、备份、dry-run 或人工维护窗口。"
        )
        json.dump(
            {
                "decision": "block",
                "reason": message,
                "hardline": True,
                "guard_rule": sorted(hardline_rule_ids)[0],
            },
            sys.stdout,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 0

    if not rule_ids:
        return 0

    message = (
        "[sensitive-guard] 检测到敏感操作信号："
        + "、".join(policy.labels(rule_ids))
        + "。执行前请确认命令意图、影响范围、验证方式和回退点；如涉及交付，写入 progress.md 的 Sensitive Operations。"
    )

    if strict_enabled(root, strict_override):
        json.dump(
            {"decision": "block", "reason": message, "guard_rule": sorted(rule_ids)[0]},
            sys.stdout,
            ensure_ascii=False,
        )
    else:
        json.dump(
            {"systemMessage": message, "guard_rule": sorted(rule_ids)[0]},
            sys.stdout,
            ensure_ascii=False,
        )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
