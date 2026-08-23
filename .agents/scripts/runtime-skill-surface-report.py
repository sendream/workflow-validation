#!/usr/bin/env python3
"""Report the visible skill/plugin surface without enabling or installing anything.

This is a derived, report-only inventory. It intentionally avoids recursive
home scans, raw config dumps, network access, package manager calls, and any
skill/plugin mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MAX_TEXT_BYTES = 128_000
MAX_MANIFESTS_PER_ROOT = 200
SECRET_HINT_RE = re.compile(r"(token|secret|password|passwd|api[_-]?key|refresh[_-]?token)", re.IGNORECASE)


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def read_text_limited(path: Path) -> tuple[str | None, str | None]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, f"read-error:{exc.__class__.__name__}"
    if len(data) > MAX_TEXT_BYTES:
        return None, "file-too-large"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "not-utf8"


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        pass
    try:
        return "~/" + path.resolve().relative_to(Path.home().resolve()).as_posix()
    except ValueError:
        return str(path)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def skill_record(path: Path, scope: str, root: Path) -> dict[str, Any]:
    text, read_error = read_text_limited(path)
    frontmatter = parse_frontmatter(text or "")
    warnings: list[str] = []
    if read_error:
        warnings.append(read_error)
    description = frontmatter.get("description", "")
    record = {
        "name": frontmatter.get("name") or path.parent.name,
        "scope": scope,
        "path": safe_rel(path, root),
        "source_kind": "skill",
        "sha256": sha256_file(path),
        "description_length": len(description),
        "has_allowed_tools": "allowed-tools" in frontmatter,
        "has_disallowed_tools": "disallowed-tools" in frontmatter,
        "has_hooks_declared": "hooks" in frontmatter,
        "warnings": warnings,
    }
    return record


def iter_skill_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    result: list[Path] = []
    for candidate in sorted(base.glob("*/SKILL.md")):
        if candidate.is_file():
            result.append(candidate)
    for candidate in sorted((base / ".system").glob("*/SKILL.md")):
        if candidate.is_file():
            result.append(candidate)
    return result


def plugin_record(path: Path, scope: str, root: Path) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    warning: str | None = None
    text, read_error = read_text_limited(path)
    if read_error:
        warning = read_error
    elif text is not None:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                payload = parsed
            else:
                warning = "manifest-not-object"
        except json.JSONDecodeError:
            warning = "invalid-json"

    raw_text = text or ""
    keys = set(payload or {})
    risk_terms = [term for term in ("mcp", "hook", "app", "server", "install", "command") if term in raw_text.lower()]
    record = {
        "name": str((payload or {}).get("name") or path.parent.parent.name),
        "version": str((payload or {}).get("version") or "unknown"),
        "scope": scope,
        "path": safe_rel(path, root),
        "source_kind": "plugin",
        "sha256": sha256_file(path),
        "manifest_keys": sorted(keys),
        "declares_mcp": "mcp" in raw_text.lower() or "mcpServers" in keys,
        "declares_hooks": "hook" in raw_text.lower() or "hooks" in keys,
        "declares_apps": "app" in raw_text.lower() or "apps" in keys,
        "risk_terms": sorted(set(risk_terms)),
        "warning": warning,
    }
    return record


def iter_plugin_manifests(codex_home: Path, project_root: Path) -> list[tuple[Path, str]]:
    roots = [
        (project_root / ".codex" / "plugins", "project"),
        (codex_home / "plugins", "codex-home"),
        (codex_home / "plugins" / "cache", "codex-home-cache"),
        (codex_home / ".tmp" / "plugins", "codex-home-tmp"),
    ]
    seen: set[Path] = set()
    result: list[tuple[Path, str]] = []
    for base, scope in roots:
        if not base.is_dir():
            continue
        count = 0
        for manifest in sorted(base.glob("**/.codex-plugin/plugin.json")):
            if manifest in seen:
                continue
            seen.add(manifest)
            result.append((manifest, scope))
            count += 1
            if count >= MAX_MANIFESTS_PER_ROOT:
                break
    return result


def config_record(path: Path, scope: str, root: Path) -> dict[str, Any]:
    text, read_error = read_text_limited(path)
    redaction = "raw-content-omitted"
    warnings: list[str] = []
    if read_error:
        warnings.append(read_error)
    if text and SECRET_HINT_RE.search(text):
        warnings.append("secret-like-key-present-redacted")
    return {
        "scope": scope,
        "path": safe_rel(path, root),
        "sha256": sha256_file(path),
        "redaction": redaction,
        "warnings": warnings,
    }


def build_report(root: Path, codex_home: Path) -> dict[str, Any]:
    warnings: list[str] = []
    sources_read: list[str] = []
    skills: list[dict[str, Any]] = []
    plugins: list[dict[str, Any]] = []
    configs: list[dict[str, Any]] = []

    skill_roots = [
        (root / ".agents" / "skills", "project"),
        (root / ".codex" / "skills", "project-codex"),
        (codex_home / "skills", "codex-home"),
    ]
    for base, scope in skill_roots:
        if base.exists():
            sources_read.append(safe_rel(base, root))
        for skill_path in iter_skill_files(base):
            skills.append(skill_record(skill_path, scope, root))

    for manifest_path, scope in iter_plugin_manifests(codex_home, root):
        sources_read.append(safe_rel(manifest_path, root))
        plugins.append(plugin_record(manifest_path, scope, root))

    for path, scope in ((root / ".codex" / "config.toml", "project"), (codex_home / "config.toml", "codex-home")):
        if path.is_file():
            sources_read.append(safe_rel(path, root))
            configs.append(config_record(path, scope, root))

    for record in plugins:
        if record.get("warning"):
            warnings.append(f"plugin manifest warning: {record['path']}: {record['warning']}")
    for record in skills:
        for warning in record.get("warnings", []):
            warnings.append(f"skill warning: {record['path']}: {warning}")

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "report-only",
        "source_of_truth": False,
        "report_only": True,
        "writes_default": False,
        "no_install": True,
        "root": ".",
        "codex_home": safe_rel(codex_home, root),
        "sources_read": sorted(set(sources_read)),
        "redactions": [
            "raw config content omitted",
            "skill body omitted except metadata-derived fields",
            "plugin manifest summarized; raw manifest content omitted",
        ],
        "limitations": [
            "does not enable, install, update, or remove skills/plugins",
            "does not call package managers, MCP servers, apps, or network",
            "does not recursively scan arbitrary home directories",
            "does not decide whether a skill/plugin should be used",
        ],
        "counts": {
            "skills": len(skills),
            "plugins": len(plugins),
            "configs": len(configs),
            "warnings": len(warnings),
        },
        "skills": skills,
        "plugins": plugins,
        "config_files": configs,
        "warnings": warnings,
    }


def emit_text(report: dict[str, Any]) -> None:
    print("status: pass")
    print("mode: report-only")
    print(f"skills: {report['counts']['skills']}")
    print(f"plugins: {report['counts']['plugins']}")
    for warning in report.get("warnings", []):
        print(f"warning: {warning}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()
    report = build_report(root, codex_home)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        emit_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
