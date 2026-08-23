#!/usr/bin/env python3
"""Single policy owner for Bash and apply_patch sensitive-operation adapters."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitiveRule:
    rule_id: str
    label: str
    severity: str


RULES = {
    rule.rule_id: rule
    for rule in (
        SensitiveRule("environment-secrets-file", "environment/secrets file", "warning"),
        SensitiveRule("ssh-material", "ssh material", "warning"),
        SensitiveRule("key-or-certificate-file", "private key/certificate", "warning"),
        SensitiveRule("credential-named-file", "token/secret keyword", "warning"),
        SensitiveRule("production-configuration", "deployment/production", "warning"),
        SensitiveRule("git-internal-path", "Git internal path", "warning"),
        SensitiveRule("git-managed-state", "Git managed state", "hardline"),
        SensitiveRule("private-key-entity", "private-key entity", "hardline"),
        SensitiveRule("sudo", "sudo", "warning"),
        SensitiveRule("destructive-remove", "destructive remove", "warning"),
        SensitiveRule("force-push", "force push", "warning"),
        SensitiveRule("git-history-rewrite", "git history rewrite", "warning"),
        SensitiveRule("database-cli", "database cli", "warning"),
        SensitiveRule("permission-ownership-change", "permission ownership change", "warning"),
        SensitiveRule("pipe-to-shell", "pipe to shell", "warning"),
        SensitiveRule("disk-filesystem-operation", "disk/filesystem operation", "warning"),
        SensitiveRule("root-filesystem-removal", "root filesystem removal", "hardline"),
        SensitiveRule("home-mount-destructive-wildcard", "home/mount destructive wildcard", "hardline"),
        SensitiveRule("fork-bomb", "fork bomb", "hardline"),
        SensitiveRule("filesystem-format", "filesystem format", "hardline"),
        SensitiveRule("raw-disk-overwrite", "raw disk overwrite", "hardline"),
        SensitiveRule("system-pipe-to-shell", "system pipe to shell", "hardline"),
    )
}

COMMAND_PATTERNS: tuple[tuple[str, str], ...] = (
    ("environment-secrets-file", r"(^|[\s'\"=:/\\])\.env(\.|$|[\s'\"=:/\\-])"),
    ("ssh-material", r"(^|[\s'\"=:/\\])\.ssh($|[\s'\"=:/\\])|authorized_keys|known_hosts|id_rsa|id_ed25519"),
    ("key-or-certificate-file", r"\.(pem|key|p12|pfx)(\s|$|['\"])"),
    ("credential-named-file", r"\b(token|secret|password|passwd|credential|apikey|api_key)\b"),
    ("sudo", r"(^|[;&|]\s*)sudo\b"),
    ("destructive-remove", r"\brm\s+(-[^\s]*[rf][^\s]*|-r|-f)\s+(/|\.|\*|~|\$HOME|/mnt/[a-z]/?)\b"),
    ("force-push", r"\bgit\s+push\b[^\n]*(--force|-f|--force-with-lease)"),
    ("git-history-rewrite", r"\bgit\s+(reset\s+--hard|clean\s+-[^\n]*[xdf]|rebase\b|filter-branch\b)"),
    ("database-cli", r"\b(psql|mysql|mongosh|mongo|redis-cli)\b"),
    ("production-configuration", r"\b(deploy|deployment|prod|production|kubectl|helm|terraform|ansible-playbook)\b"),
    ("permission-ownership-change", r"\b(chmod\s+777|chmod\s+-R|chown\s+-R)\b"),
    ("pipe-to-shell", r"\b(curl|wget)\b[^\n|]*\|\s*(sh|bash)\b"),
    ("disk-filesystem-operation", r"\b(dd|mkfs|mount|umount|truncate)\b"),
    ("git-internal-path", r"(^|[\s'\"=:])\.git[/\\]"),
)

COMMAND_HARDLINE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("root-filesystem-removal", r"\brm\s+(-[^\s]*[rf][^\s]*|-r|-f)\s+(--no-preserve-root\s+)?/(\s|$)"),
    ("home-mount-destructive-wildcard", r"\brm\s+(-[^\s]*[rf][^\s]*|-r|-f)\s+(~|\$HOME|/mnt/[a-z]/?|\*)\s*$"),
    ("fork-bomb", r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
    ("filesystem-format", r"\bmkfs(\.[a-z0-9]+)?\b[^\n]*(/dev/[a-z]+|/dev/nvme|/dev/mapper)"),
    ("raw-disk-overwrite", r"\bdd\b[^\n]*(of=/dev/(sd[a-z]|vd[a-z]|xvd[a-z]|nvme\d+n\d+|mapper/)[^\s]*)"),
    ("system-pipe-to-shell", r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(sh|bash)\b"),
)

PRIVATE_KEY_MARKER_RE = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----|-----BEGIN OPENSSH PRIVATE KEY-----",
    re.IGNORECASE,
)
ENV_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])\.env(?:[.-][A-Za-z0-9_-]+)?", re.IGNORECASE)
GIT_TRANSACTION_FILES = {
    "merge_head",
    "merge_mode",
    "merge_msg",
    "cherry_pick_head",
    "revert_head",
    "rebase_head",
    "auto_merge",
    "squash_msg",
}


def path_parts(path: str) -> tuple[str, ...]:
    return tuple(part for part in path.replace("\\", "/").split("/") if part not in {"", "."})


def env_example_exempt(path: str) -> bool:
    parts = path_parts(path)
    name = parts[-1].lower() if parts else ""
    return name.startswith(".env") and name.endswith((".example", ".sample", ".template"))


def git_relative_parts(path: str) -> tuple[str, ...] | None:
    parts = path_parts(path)
    git_index = next((index for index, part in enumerate(parts) if part.lower() == ".git"), None)
    if git_index is None:
        return None
    return parts[git_index + 1 :]


def hardline_git_state(path: str) -> bool:
    relative = git_relative_parts(path)
    if not relative:
        return False
    first = relative[0].lower()
    if first in {"head", "index", "index.lock", "packed-refs", "packed-refs.lock"}:
        return True
    if first in {"objects", "refs", "logs", "rebase-apply", "rebase-merge", "sequencer"}:
        return True
    return first in GIT_TRANSACTION_FILES


def edit_path_rule_ids(path: str) -> set[str]:
    normalized = path.replace("\\", "/")
    lowered = normalized.lower()
    parts = path_parts(path)
    name = parts[-1].lower() if parts else ""
    rules: set[str] = set()

    if git_relative_parts(path) is not None:
        rules.add("git-internal-path")
    if (name == ".env" or name.startswith(".env.")) and not env_example_exempt(path):
        rules.add("environment-secrets-file")
    if ".ssh" in {part.lower() for part in parts} or name in {"authorized_keys", "known_hosts", "id_rsa", "id_ed25519"}:
        rules.add("ssh-material")
    if posixpath.splitext(name)[1] in {".pem", ".key", ".p12", ".pfx"}:
        rules.add("key-or-certificate-file")
    if re.search(r"(?:^|[-_.])(token|secret|password|passwd|credential|apikey|api_key)(?:[-_.]|$)", name):
        rules.add("credential-named-file")
    if re.search(r"(?:^|/)(?:config/)?(?:prod|production)(?:[./_-]|$)", lowered) or re.search(
        r"(?:^|[._-])(?:prod|production)(?:[._-]|$)", name
    ):
        rules.add("production-configuration")
    return rules


def _only_env_template_mentions(command: str) -> bool:
    mentions = ENV_MENTION_RE.findall(command)
    return bool(mentions) and all(env_example_exempt(mention) for mention in mentions)


def command_rule_ids(command: str) -> set[str]:
    rules: set[str] = set()
    for rule_id, pattern in COMMAND_PATTERNS:
        if not re.search(pattern, command, flags=re.IGNORECASE):
            continue
        if rule_id == "environment-secrets-file" and _only_env_template_mentions(command):
            continue
        rules.add(rule_id)
    return rules


def command_hardline_rule_ids(command: str) -> set[str]:
    return {
        rule_id
        for rule_id, pattern in COMMAND_HARDLINE_PATTERNS
        if re.search(pattern, command, flags=re.IGNORECASE)
    }


def patch_content_hardline_rule_ids(command: str) -> set[str]:
    return {"private-key-entity"} if PRIVATE_KEY_MARKER_RE.search(command) else set()


def labels(rule_ids: set[str]) -> list[str]:
    return sorted(RULES[rule_id].label for rule_id in rule_ids)
