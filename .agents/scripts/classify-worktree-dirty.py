#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SENSITIVE_MARKERS = (
    ".env",
    ".ssh/",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    "token",
    "secret",
    "credential",
    "auth.json",
)

GENERATED_MARKERS = (
    "node_modules/",
    "dist/",
    "build/",
    "target/",
    "__pycache__/",
    ".pyc",
    ".log",
    ".zip",
    ".tgz",
    ".tar",
    ".tar.gz",
    ".dump",
    ".bak",
    ".har",
    ".trace",
    ".db",
    ".sqlite",
    ".rdb",
    ".aof",
    "dump.rdb",
    "appendonly.aof",
    "weaviate/",
    "milvus/",
    "elasticsearch/",
    "redis/",
    "postgres-data/",
    "mysql-data/",
    "graphify-out/",
    ".codegraph/",
    "codegraph-out/",
    ".codex-tmp/",
    ".agent-state/",
    ".agents/runs/",
)

STRUCTURAL_INDEX_MARKERS = (
    "graphify-out/",
    ".codegraph/",
    "codegraph-out/",
)

AGENT_ARCHIVE_MARKERS = (
    ".agent-state/",
    ".agents/tasks/",
    ".agents/runs/",
    ".agents/state/",
)

WORKFLOW_MARKERS = (
    ".agents/",
    ".codex/",
    "AGENTS.md",
    "code_review.md",
    "task_plan.md",
    "findings.md",
    "progress.md",
)


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def git_root(root: Path) -> Path | None:
    result = run_git(root, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def parse_status(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({"status": status, "path": path})
    return entries


def parse_name_status(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1] if len(parts) > 1 else ""
        entries.append({"status": status, "path": path})
    return entries


def has_marker(path: str, markers: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(marker.lower() in normalized for marker in markers)


def classify(path: str) -> str:
    if has_marker(path, SENSITIVE_MARKERS):
        return "sensitive"
    if has_marker(path, GENERATED_MARKERS):
        return "generated"
    if has_marker(path, WORKFLOW_MARKERS):
        return "workflow-state"
    return "source-or-doc"


def context_group(path: str, category: str) -> str:
    if has_marker(path, AGENT_ARCHIVE_MARKERS):
        return "agent-state-or-archive"
    if has_marker(path, STRUCTURAL_INDEX_MARKERS):
        return "generated-or-structural-index"
    if category == "sensitive":
        return "runtime-or-sensitive"
    if has_marker(path, ("redis/", "weaviate/", "milvus/", "elasticsearch/", "postgres-data/", "mysql-data/")):
        return "runtime-or-sensitive"
    if category == "generated":
        return "generated-or-structural-index"
    if category == "workflow-state":
        return "workflow"
    if category == "source-or-doc":
        return "source"
    return "unknown"


def file_size(root: Path, path: str) -> int | None:
    candidate = root / path
    try:
        if candidate.is_file():
            return candidate.stat().st_size
    except OSError:
        return None
    return None


def build_payload(root: Path, large_threshold: int, staged_only: bool) -> dict[str, Any]:
    resolved_root = root.resolve()
    top = git_root(resolved_root)
    payload: dict[str, Any] = {
        "root": str(resolved_root),
        "git_root": str(top) if top else None,
        "is_git_root": top == resolved_root if top else False,
        "mode": "staged" if staged_only else "worktree",
        "categories": {
            "sensitive": [],
            "generated": [],
            "workflow-state": [],
            "source-or-doc": [],
            "large": [],
        },
        "context_groups": {
            "workflow": [],
            "source": [],
            "runtime-or-sensitive": [],
            "generated-or-structural-index": [],
            "generated-or-graphify": [],
            "agent-state-or-archive": [],
            "unknown": [],
        },
        "summary": {},
        "context_summary": {},
        "warnings": [],
    }

    if top is None:
        payload["warnings"].append("not-a-git-worktree")
        return payload
    if top != resolved_root:
        payload["warnings"].append("root-is-inside-another-git-worktree")

    if staged_only:
        status = run_git(resolved_root, ["diff", "--cached", "--name-status"])
    else:
        status = run_git(resolved_root, ["status", "--porcelain=v1"])
    if status.returncode != 0:
        payload["warnings"].append("git-status-failed" if not staged_only else "git-staged-diff-failed")
        payload["stderr"] = status.stderr.strip()
        return payload

    entries = parse_name_status(status.stdout) if staged_only else parse_status(status.stdout)
    for entry in entries:
        path = entry["path"]
        category = classify(path)
        size = file_size(top, path)
        item: dict[str, Any] = {"status": entry["status"], "path": path}
        if size is not None:
            item["bytes"] = size
        payload["categories"][category].append(item)
        group = context_group(path, category)
        payload["context_groups"].setdefault(group, []).append(item)
        if group == "generated-or-structural-index":
            payload["context_groups"].setdefault("generated-or-graphify", []).append(item)
        if size is not None and size >= large_threshold:
            payload["categories"]["large"].append(item)

    payload["summary"] = {key: len(value) for key, value in payload["categories"].items()}
    payload["context_summary"] = {key: len(value) for key, value in payload["context_groups"].items()}
    return payload


def emit_summary(payload: dict[str, Any]) -> None:
    print(f"root: {payload['root']}")
    print(f"git_root: {payload['git_root'] or 'none'}")
    if payload["warnings"]:
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    print("context summary:")
    for key, count in payload.get("context_summary", {}).items():
        print(f"- {key}: {count}")
    print("risk summary:")
    for key in ("sensitive", "generated", "workflow-state", "source-or-doc", "large"):
        print(f"- {key}: {payload.get('summary', {}).get(key, 0)}")
    print("top examples:")
    for key in ("runtime-or-sensitive", "generated-or-structural-index", "generated-or-graphify", "agent-state-or-archive", "workflow", "source", "unknown"):
        items = payload.get("context_groups", {}).get(key, [])
        if not items:
            continue
        print(f"{key}:")
        for item in items[:10]:
            suffix = f" ({item['bytes']} bytes)" if "bytes" in item else ""
            print(f"- {item['status']} {item['path']}{suffix}")
        if len(items) > 10:
            print(f"- ... {len(items) - 10} more")


def emit_text(payload: dict[str, Any]) -> None:
    print(f"root: {payload['root']}")
    print(f"git_root: {payload['git_root'] or 'none'}")
    if payload["warnings"]:
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    print("summary:")
    for key, count in payload["summary"].items():
        print(f"- {key}: {count}")
    for key in ("sensitive", "generated", "workflow-state", "source-or-doc", "large"):
        items = payload["categories"].get(key, [])
        if not items:
            continue
        print(f"{key}:")
        for item in items[:50]:
            print(f"- {item['status']} {item['path']}")
        if len(items) > 50:
            print(f"- ... {len(items) - 50} more")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify dirty git worktree entries for push gates.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--format", choices=("text", "json", "summary"), default="text")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit a low-noise grouped summary. Equivalent to --format summary.",
    )
    parser.add_argument("--large-threshold-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Classify only staged changes using git diff --cached --name-status.",
    )
    parser.add_argument(
        "--fail-on-risk",
        action="store_true",
        help="Exit 2 when sensitive, generated, or large dirty entries are present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.summary:
        args.format = "summary"
    payload = build_payload(Path(args.root), args.large_threshold_bytes, args.staged_only)
    if args.format == "json":
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif args.format == "summary":
        emit_summary(payload)
    else:
        emit_text(payload)

    risky = (
        len(payload["categories"].get("sensitive", []))
        + len(payload["categories"].get("generated", []))
        + len(payload["categories"].get("large", []))
    )
    return 2 if args.fail_on_risk and risky else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
