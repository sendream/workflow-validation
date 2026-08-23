#!/usr/bin/env python3
"""Validate repo-local workflow skills against the Codex skill contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "metadata", "license", "allowed-tools"}
DISALLOWED_AUX_FILES = {
    "README.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CHANGELOG.md",
}
STRICT_REQUIRED_SECTIONS = {
    "forbidden actions": "Forbidden Actions",
    "validation": "Validation",
    "references boundary": "References Boundary",
}
WORKFLOW_METADATA_SECTION = "Workflow Metadata"
WORKFLOW_METADATA_FIELDS = {
    "scope",
    "trigger_evidence",
    "negative_trigger",
    "precedence",
    "conflicts",
    "input_budget",
    "output_contract",
    "owner_source",
    "source_digest",
    "validation",
}
COMPATIBILITY_SKILLS = {
    "planning-with-files": "Planning With Files",
    "requirements-to-plan": "Requirements To Plan",
    "ship-check": "Ship Check",
    "project-context": "Project Context",
}
BROAD_TRIGGER_RE = re.compile(r"\b(always|every task|all tasks|any task)\b", re.IGNORECASE)
PROJECT_SPECIFIC_RE = re.compile(
    r"(/home/|/mnt/|/var/www/|/opt/|/srv/|[A-Za-z]:\\|\b\d{1,3}(?:\.\d{1,3}){3}\b|[\w.-]+\.(?:local|internal|lan|corp)\b)",
    re.IGNORECASE,
)
TRIGGER_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "any",
        "by",
        "complex",
        "for",
        "from",
        "in",
        "is",
        "need",
        "needs",
        "of",
        "on",
        "or",
        "task",
        "tasks",
        "the",
        "to",
        "when",
        "with",
    }
)
TRIGGER_TERM_RE = re.compile(r"[a-z0-9]+")


def parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str, skill_md: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, [f"{skill_md}: missing YAML frontmatter"]

    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not match:
        return {}, [f"{skill_md}: invalid YAML frontmatter boundary"]

    data: dict[str, str] = {}
    for line_number, line in enumerate(match.group(1).splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            errors.append(f"{skill_md}:{line_number}: unsupported frontmatter line")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in ALLOWED_FRONTMATTER_KEYS:
            allowed = ", ".join(sorted(ALLOWED_FRONTMATTER_KEYS))
            errors.append(f"{skill_md}:{line_number}: unexpected key '{key}' (allowed: {allowed})")
            continue
        data[key] = parse_scalar(value)

    return data, errors


def has_section(text: str, section_name: str) -> bool:
    pattern = re.compile(rf"^##+\s+{re.escape(section_name)}\s*$", re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(text))


def section_text(text: str, section_name: str) -> str:
    pattern = re.compile(
        rf"^##+\s+{re.escape(section_name)}\s*$([\s\S]*?)(?=^##+\s|\Z)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


def parse_workflow_metadata(text: str, skill_md: Path) -> tuple[dict[str, str], list[str]]:
    section = section_text(text, WORKFLOW_METADATA_SECTION)
    if not section:
        return {}, [f"{skill_md}: missing required section '{WORKFLOW_METADATA_SECTION}'"]
    table_lines = [line for line in section.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return {}, [f"{skill_md}: Workflow Metadata must contain a field/value table"]

    def cells(line: str) -> list[str]:
        return [part.strip() for part in line.strip().strip("|").split("|")]

    header = [cell.lower().replace(" ", "_") for cell in cells(table_lines[0])]
    if header != ["field", "value"]:
        return {}, [f"{skill_md}: Workflow Metadata table must use field/value columns"]
    metadata: dict[str, str] = {}
    errors: list[str] = []
    for line_number, line in enumerate(table_lines[2:], start=3):
        row = cells(line)
        if len(row) != 2:
            errors.append(f"{skill_md}: Workflow Metadata row {line_number} must have two columns")
            continue
        key = row[0].strip().lower().replace(" ", "_")
        if not key:
            errors.append(f"{skill_md}: Workflow Metadata row {line_number} has an empty field")
            continue
        if key in metadata:
            errors.append(f"{skill_md}: Workflow Metadata repeats '{key}'")
            continue
        metadata[key] = row[1].strip()
    return metadata, errors


def owner_source_digest(root: Path, owner_source: str) -> tuple[str | None, list[str]]:
    """Validate a repo-local owner link and return its whole-file digest.

    The anchor makes the link human-specific; whole-file digests deliberately
    force a small metadata refresh whenever the owning Gate Card changes.
    """

    if "#" not in owner_source:
        return None, ["owner_source must include a #heading anchor"]
    path_value, anchor = owner_source.split("#", 1)
    path_value = path_value.strip()
    anchor = anchor.strip()
    if not path_value or not anchor:
        return None, ["owner_source must contain a path and heading anchor"]
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None, ["owner_source must stay under the project root"]
    source_path = root / relative_path
    try:
        source_path.resolve(strict=False).relative_to(root.resolve())
    except ValueError:
        return None, ["owner_source escapes the project root"]
    if not source_path.is_file():
        return None, [f"owner_source file is missing: {path_value}"]
    source_text = source_path.read_text(encoding="utf-8")
    anchor_re = re.compile(rf"^#+\s+{re.escape(anchor)}\s*$", re.IGNORECASE | re.MULTILINE)
    if not anchor_re.search(source_text):
        return None, [f"owner_source heading is missing: {owner_source}"]
    return hashlib.sha256(source_path.read_bytes()).hexdigest(), []


def higher_precedence_targets(value: str) -> set[str]:
    if value.strip().lower() in {"", "none", "not-needed"}:
        return set()
    match = re.fullmatch(r"higher-than\s*:\s*([a-z0-9][a-z0-9,\-\s]*)", value.strip(), re.IGNORECASE)
    if not match:
        return set()
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def mutually_exclusive_targets(value: str) -> set[str]:
    if value.strip().lower() in {"", "none", "not-needed"}:
        return set()
    match = re.fullmatch(r"mutually-exclusive\s*:\s*([a-z0-9][a-z0-9,\-\s]*)", value.strip(), re.IGNORECASE)
    if not match:
        return set()
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def trigger_terms(value: str) -> set[str]:
    """Return the bounded, meaningful English terms in trigger metadata.

    Exact equality remains the strongest ambiguity signal.  This secondary
    check deliberately catches only a two-or-more-term overlap, so a generic
    word such as ``task`` cannot turn all local skills into a conflict.
    Non-English trigger metadata still receives exact-match protection; its
    semantic routing must be owned by an explicit Gate Card instead of an
    unsafe tokenizer heuristic here.
    """

    return {
        term
        for term in TRIGGER_TERM_RE.findall(value.lower())
        if len(term) >= 3 and term not in TRIGGER_STOPWORDS
    }


def has_precedence_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(target) for target in graph.get(node, set())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_skill(skill_dir: Path, root: Path, *, strict_quality: bool = False) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"], {}

    text = skill_md.read_text(encoding="utf-8")
    frontmatter, parse_errors = parse_frontmatter(text, skill_md)
    errors.extend(parse_errors)

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()

    if not name:
        errors.append(f"{skill_md}: missing frontmatter field 'name'")
    elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append(f"{skill_md}: name must be lowercase hyphen-case")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(f"{skill_md}: name is longer than {MAX_NAME_LENGTH} characters")
    elif name != skill_dir.name:
        errors.append(f"{skill_md}: name '{name}' must match folder '{skill_dir.name}'")

    if not description:
        errors.append(f"{skill_md}: missing frontmatter field 'description'")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"{skill_md}: description is longer than {MAX_DESCRIPTION_LENGTH} characters")
    elif "<" in description or ">" in description:
        errors.append(f"{skill_md}: description must not contain angle brackets")
    elif strict_quality and BROAD_TRIGGER_RE.search(description):
        errors.append(f"{skill_md}: description must not use broad always-on trigger language")

    if strict_quality:
        for section_key, section_label in STRICT_REQUIRED_SECTIONS.items():
            if not has_section(text, section_label):
                errors.append(f"{skill_md}: missing required section '{section_label}'")
        if PROJECT_SPECIFIC_RE.search(text):
            errors.append(f"{skill_md}: project-specific literal must live in .agents/references, not SKILL.md")

    metadata: dict[str, str] = {}
    if strict_quality:
        metadata, metadata_errors = parse_workflow_metadata(text, skill_md)
        errors.extend(metadata_errors)
        missing_fields = sorted(field for field in WORKFLOW_METADATA_FIELDS if not metadata.get(field, "").strip())
        if missing_fields:
            errors.append(f"{skill_md}: Workflow Metadata missing fields: {', '.join(missing_fields)}")
        input_budget = metadata.get("input_budget", "")
        if input_budget and not re.fullmatch(r"<=?\s*\d+\s+tokens?", input_budget, re.IGNORECASE):
            errors.append(f"{skill_md}: Workflow Metadata input_budget must be a bounded token count")
        owner_source = metadata.get("owner_source", "")
        source_digest = metadata.get("source_digest", "")
        if owner_source:
            expected_digest, owner_errors = owner_source_digest(root, owner_source)
            errors.extend(f"{skill_md}: Workflow Metadata {error}" for error in owner_errors)
            if expected_digest is not None:
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", source_digest):
                    errors.append(f"{skill_md}: Workflow Metadata source_digest must be sha256:<64 lowercase hex>")
                elif source_digest != f"sha256:{expected_digest}":
                    errors.append(f"{skill_md}: Workflow Metadata source_digest is stale for {owner_source}")

    for filename in DISALLOWED_AUX_FILES:
        if (skill_dir / filename).exists():
            errors.append(f"{skill_dir / filename}: auxiliary docs do not belong in a skill")

    return errors, metadata


def validate_compatibility_skill(skill_dir: Path, expected_title: str, metadata: dict[str, str]) -> list[str]:
    """Check the opt-in package contract for a retained legacy wrapper."""

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    text = skill_md.read_text(encoding="utf-8")
    errors: list[str] = []
    title = f"# {expected_title} (Compatibility Only)"
    if title not in text.splitlines():
        errors.append(f"{skill_md}: missing Compatibility Only title marker")
    if "Compatibility marker for older installs" not in text:
        errors.append(f"{skill_md}: missing legacy-install compatibility marker")
    if "New tasks must not route through this wrapper." not in text:
        errors.append(f"{skill_md}: missing current/new-task no-route contract")
    if metadata.get("scope", "").strip().lower() != "compatibility-only pointer":
        errors.append(f"{skill_md}: Workflow Metadata scope must be compatibility-only pointer")
    if "new task" not in metadata.get("negative_trigger", "").lower() or "current direct" not in metadata.get("negative_trigger", "").lower():
        errors.append(f"{skill_md}: Workflow Metadata negative_trigger must exclude new and current direct routes")
    if metadata.get("precedence", "").strip().lower() != "none":
        errors.append(f"{skill_md}: Workflow Metadata precedence must be none")
    if metadata.get("conflicts", "").strip().lower() != "none":
        errors.append(f"{skill_md}: Workflow Metadata conflicts must be none")
    if "redirect" not in metadata.get("output_contract", "").lower():
        errors.append(f"{skill_md}: Workflow Metadata output_contract must redirect to the direct contract")
    return errors


def skill_dirs(root: Path) -> list[Path]:
    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(path.parent for path in skills_root.glob("*/SKILL.md"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root_arg", nargs="?", help="Project root containing .agents/skills")
    parser.add_argument("--root", dest="root_opt", help="Project root containing .agents/skills")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict-quality",
        action="store_true",
        help="Enforce trigger, forbidden action, validation, references-boundary, and project-literal quality checks.",
    )
    parser.add_argument(
        "--require-compatibility-skills",
        action="store_true",
        help="Require the starter-pack's four retained compatibility-only wrapper skills.",
    )
    args = parser.parse_args(argv)
    if args.require_compatibility_skills and not args.strict_quality:
        parser.error("--require-compatibility-skills requires --strict-quality")

    root_value = args.root_opt or args.root_arg or "."
    root = Path(root_value).resolve()
    dirs = skill_dirs(root)
    if not dirs:
        result = {
            "status": "fail",
            "root": str(root),
            "strict_quality": args.strict_quality,
            "checked_skills": 0,
            "errors": [f"no repo-local skills found under {root}/.agents/skills"],
        }
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"fail: {result['errors'][0]}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    passed: list[str] = []
    metadata_by_skill: dict[str, dict[str, str]] = {}
    for directory in dirs:
        errors, metadata = validate_skill(directory, root, strict_quality=args.strict_quality)
        metadata_by_skill[directory.name] = metadata
        if errors:
            all_errors.extend(errors)
        else:
            passed.append(str(directory.relative_to(root)))
            if args.format == "text":
                print(f"pass: skill contract {directory.relative_to(root)}")

    if args.require_compatibility_skills:
        for name, title in COMPATIBILITY_SKILLS.items():
            skill_dir = root / ".agents" / "skills" / name
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                all_errors.append(f"missing required compatibility skill: .agents/skills/{name}/SKILL.md")
                continue
            all_errors.extend(validate_compatibility_skill(skill_dir, title, metadata_by_skill.get(name, {})))

    if args.strict_quality:
        skill_names = set(metadata_by_skill)
        precedence_graph: dict[str, set[str]] = {name: set() for name in skill_names}
        exclusions: dict[str, set[str]] = {name: set() for name in skill_names}
        for name, metadata in metadata_by_skill.items():
            for target in higher_precedence_targets(metadata.get("precedence", "")):
                if target not in skill_names:
                    all_errors.append(f"{root / '.agents/skills' / name / 'SKILL.md'}: Workflow Metadata precedence references unknown skill '{target}'")
                else:
                    precedence_graph[name].add(target)
            for target in mutually_exclusive_targets(metadata.get("conflicts", "")):
                if target not in skill_names:
                    all_errors.append(f"{root / '.agents/skills' / name / 'SKILL.md'}: Workflow Metadata conflicts references unknown skill '{target}'")
                else:
                    exclusions[name].add(target)
        if has_precedence_cycle(precedence_graph):
            all_errors.append("Workflow Metadata precedence contains a cycle")
        ordered_names = sorted(skill_names)
        for index, left in enumerate(ordered_names):
            for right in ordered_names[index + 1 :]:
                left_trigger = metadata_by_skill[left].get("trigger_evidence", "").strip().lower()
                right_trigger = metadata_by_skill[right].get("trigger_evidence", "").strip().lower()
                if not left_trigger or not right_trigger:
                    continue
                shared_terms = trigger_terms(left_trigger) & trigger_terms(right_trigger)
                if left_trigger != right_trigger and len(shared_terms) < 2:
                    continue
                resolved = (
                    right in precedence_graph[left]
                    or left in precedence_graph[right]
                    or right in exclusions[left]
                    or left in exclusions[right]
                )
                if not resolved:
                    overlap_detail = "share trigger_evidence" if left_trigger == right_trigger else (
                        "share trigger terms: " + ", ".join(sorted(shared_terms))
                    )
                    all_errors.append(
                        "Workflow Metadata ambiguous simultaneous trigger: "
                        f"{left} and {right} {overlap_detail} without precedence or mutual exclusion"
                    )

    result = {
        "status": "fail" if all_errors else "pass",
        "root": str(root),
        "strict_quality": args.strict_quality,
        "require_compatibility_skills": args.require_compatibility_skills,
        "checked_skills": len(dirs),
        "passed": passed,
        "workflow_metadata": metadata_by_skill if args.strict_quality else {},
        "errors": all_errors,
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for error in all_errors:
            print(f"fail: {error}", file=sys.stderr)

    if all_errors:
        return 1

    if args.format == "text":
        print(f"pass: validated {len(dirs)} repo-local skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
