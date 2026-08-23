---
name: planning-with-files
description: Compatibility marker for older installs; new tasks maintain active state directly from AGENTS.md and core templates.
---

# Planning With Files (Compatibility Only)

New tasks must not route through this wrapper. When an active complex task uses the three root files, follow `AGENTS.md`, the current snapshot, the core templates, and the directly triggered workflow reference.

## Workflow Metadata

| field | value |
|---|---|
| scope | compatibility-only pointer |
| trigger_evidence | a migrated installation invokes the literal planning-with-files wrapper |
| negative_trigger | every new task and every current direct-state route |
| precedence | none |
| conflicts | none |
| input_budget | <= 120 tokens |
| output_contract | redirect to direct three-file maintenance without loading another workflow layer |
| owner_source | .agents/references/workflow/routing-planning.md#Template Scaling |
| source_digest | sha256:89f0f81fa70cba92956ec8458e2866d668236a76458ab9abd60dafe51e6f2b4b |
| validation | python3 .agents/scripts/validate-local-skills.py --root . --strict-quality |

## Forbidden Actions

- Do not treat this compatibility file as a Gate, task state, implementation authorization, or reason to create three files for a fast/read-only task.
- Do not copy task state, project facts, evidence, or workflow policy into this file.

## Validation

- Confirm that current routes do not return this Skill and that complex active tasks still load the three root files directly.
- Run the local Skill validator and the affected deterministic behavior tests after changing this compatibility pointer.

## References Boundary

- Current state maintenance is owned by `AGENTS.md`, the three core templates, and directly triggered `workflow/*.md` sections.
- This file may be removed only when installed-package cleanup can remove stale Skill files safely.
