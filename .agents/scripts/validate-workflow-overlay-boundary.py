#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_OVERLAY_FILES = (
    "AGENTS.md",
    "code_review.md",
    ".rgignore",
    ".geminiignore",
    ".repomixignore",
    ".aiderignore",
    ".graphifyignore",
    ".agent-state/README.md",
    ".agents/references/workflow-details.md",
    ".agents/references/workflow/gate-cards.md",
    ".agents/references/workflow/routing-planning.md",
    ".agents/references/workflow/context-memory.md",
    ".agents/references/workflow/reviewer-governance.md",
    ".agents/references/workflow/verification-evidence.md",
    ".agents/references/workflow/lifecycle-recovery.md",
    ".agents/references/workflow/tooling-safety.md",
    ".agents/references/workflow/evolution-experiments.md",
    ".agents/references/project-conventions.md",
    ".agents/references/common-pitfalls.md",
    ".agents/references/tooling-map.md",
    ".agents/references/validator-map.md",
    ".agents/skills/planning-with-files/SKILL.md",
    ".agents/skills/requirements-to-plan/SKILL.md",
    ".agents/skills/ship-check/SKILL.md",
    ".agents/skills/project-context/SKILL.md",
    ".agents/templates/task_plan.md",
    ".agents/templates/progress.md",
    ".agents/templates/findings.md",
    ".agents/templates/capability-card.md",
    ".agents/scripts/workflow_routing.py",
    ".agents/scripts/markdown_table.py",
    ".agents/scripts/markdown_document.py",
    ".agents/scripts/validator_result.py",
    ".agents/scripts/context-select.py",
    ".agents/scripts/context_selection_contract.py",
    ".agents/scripts/current_task_snapshot.py",
    ".agents/scripts/state_compat.py",
    ".agents/scripts/state-compat.py",
    ".agents/scripts/validate-capability-card.py",
    ".agents/scripts/harness_components.py",
    ".agents/scripts/run_manifest_contract.py",
    ".agents/scripts/portable.sh",
    ".agents/scripts/classify-worktree-dirty.py",
    ".agents/scripts/validate-active-task-migration.py",
    ".agents/scripts/validate-evidence-waivers.py",
    ".agents/scripts/validate-review-authorization.py",
    ".agents/scripts/validate-release-artifact-source.py",
    ".agents/scripts/validate-role-review-packet.py",
    ".agents/scripts/validate-reviewer-assessment.py",
    ".agents/scripts/validate-workflow-overlay-boundary.py",
    ".agents/scripts/sensitive-command-guard.py",
    ".agents/scripts/sensitive_guard_policy.py",
    ".agents/scripts/hook_event_contract.py",
    ".agents/scripts/sensitive-edit-guard.py",
    ".agents/scripts/trajectory-monitor.py",
    ".agents/scripts/capture-run-script.sh",
    ".agents/scripts/archive-legacy-runs.sh",
    ".agents/scripts/search-workflow-history.py",
    ".agents/scripts/verify-workflow-smoke.sh",
)

WORKFLOW_PATHS = (
    "AGENTS.md",
    "GEMINI.md",
    "code_review.md",
    "task_plan.md",
    "progress.md",
    "findings.md",
    ".agents/",
    ".agent-state/",
    ".codex/",
    ".rgignore",
    ".geminiignore",
    ".repomixignore",
    ".aiderignore",
    ".graphifyignore",
    ".codegraph/",
    "codegraph-out/",
)

LOCAL_EXCLUDE_PATTERNS = (
    "/AGENTS.md",
    "/code_review.md",
    "/task_plan.md",
    "/progress.md",
    "/findings.md",
    "/.agents/",
    "/.agent-state/",
    "/.rgignore",
    "/.geminiignore",
    "/.repomixignore",
    "/.aiderignore",
    "/.graphifyignore",
    "/.codegraph/",
    "**/.codegraph/",
    "/codegraph-out/",
    "**/codegraph-out/",
    "/.codex/",
)


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def is_git_worktree(root: Path) -> bool:
    return run_git(root, ["rev-parse", "--is-inside-work-tree"]).returncode == 0


def normalized(path: str) -> str:
    rel = path.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def is_workflow_path(path: str) -> bool:
    rel = normalized(path)
    parts = set(rel.split("/"))
    for marker in WORKFLOW_PATHS:
        marker_rel = marker.strip("/")
        if rel == marker_rel or rel.startswith(marker):
            return True
        if marker.endswith("/") and marker_rel in parts:
            return True
    return False


def parse_name_status(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1] if len(parts) > 1 else ""
        rows.append({"status": status, "path": path})
    return rows


def parse_porcelain(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        rows.append({"status": status, "path": path})
    return rows


def missing_required(root: Path) -> list[str]:
    return [path for path in REQUIRED_OVERLAY_FILES if not (root / path).is_file()]


def workflow_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [entry for entry in entries if is_workflow_path(entry["path"])]


def deletion_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    deleted: list[dict[str, str]] = []
    for entry in entries:
        status = entry["status"]
        if "D" in status and is_workflow_path(entry["path"]):
            deleted.append(entry)
    return deleted


def local_exclude_status(root: Path) -> dict[str, Any]:
    info_exclude = root / ".git" / "info" / "exclude"
    gitignore = root / ".gitignore"
    sources: dict[str, list[str]] = {}

    for label, path in (("git_info_exclude", info_exclude), ("gitignore", gitignore)):
        if path.is_file():
            try:
                sources[label] = [
                    line.strip()
                    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                ]
            except OSError:
                sources[label] = []
        else:
            sources[label] = []

    covered = {
        pattern: any(pattern == line or pattern.lstrip("/") == line.lstrip("/") for lines in sources.values() for line in lines)
        for pattern in LOCAL_EXCLUDE_PATTERNS
    }
    return {
        "sources": sources,
        "covered": covered,
        "missing": [pattern for pattern, ok in covered.items() if not ok],
        "status": "pass" if all(covered.values()) else "warn",
    }


def validate(root: Path, staged_only: bool, require_local_exclude: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "root": str(root),
        "status": "pass",
        "errors": [],
        "warnings": [],
        "missing_required": missing_required(root),
        "staged_workflow_entries": [],
        "staged_workflow_deletions": [],
        "worktree_workflow_deletions": [],
        "local_exclude": local_exclude_status(root),
    }

    if result["missing_required"]:
        result["errors"].append("missing required local workflow overlay files")

    if not is_git_worktree(root):
        result["warnings"].append("not a git worktree; skipped staged/deletion checks")
    else:
        staged = run_git(root, ["diff", "--cached", "--name-status"])
        if staged.returncode != 0:
            result["errors"].append("git staged diff failed")
            result["git_stderr"] = staged.stderr.strip()
        else:
            staged_entries = parse_name_status(staged.stdout)
            result["staged_workflow_entries"] = workflow_entries(staged_entries)
            result["staged_workflow_deletions"] = deletion_entries(staged_entries)
            if result["staged_workflow_entries"]:
                result["errors"].append("workflow overlay files are staged; keep them local unless explicitly authorized")
            if result["staged_workflow_deletions"]:
                result["errors"].append("workflow overlay deletions are staged; use git rm --cached or local exclude, do not delete local overlay")

        if not staged_only:
            status = run_git(root, ["status", "--porcelain=v1"])
            if status.returncode != 0:
                result["errors"].append("git status failed")
                result["git_status_stderr"] = status.stderr.strip()
            else:
                result["worktree_workflow_deletions"] = deletion_entries(parse_porcelain(status.stdout))
                if result["worktree_workflow_deletions"]:
                    result["errors"].append("workflow overlay files are deleted in the worktree")

    if result["local_exclude"]["missing"]:
        message = "local workflow overlay ignore patterns are incomplete"
        if require_local_exclude:
            result["errors"].append(message)
        else:
            result["warnings"].append(message)

    if result["errors"]:
        result["status"] = "fail"
    elif result["warnings"]:
        result["status"] = "warn"
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate that local workflow overlay files are present but not staged for delivery.")
    parser.add_argument("--root", default=".", help="Project root to inspect.")
    parser.add_argument("--staged-only", action="store_true", help="Only inspect staged changes, not worktree deletions.")
    parser.add_argument("--require-local-exclude", action="store_true", help="Fail if .git/info/exclude or .gitignore lacks workflow overlay patterns.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    payload = validate(Path(args.root).resolve(), args.staged_only, args.require_local_exclude)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        for error in payload["errors"]:
            print(f"error: {error}", file=sys.stderr)
        for warning in payload["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
        if payload["missing_required"]:
            print("missing required files:")
            for path in payload["missing_required"]:
                print(f"- {path}")
        if payload["staged_workflow_entries"]:
            print("staged workflow entries:")
            for entry in payload["staged_workflow_entries"]:
                print(f"- {entry['status']} {entry['path']}")
    return 1 if payload["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
