---
name: project-context
description: Compatibility marker for older installs; new tasks use direct project orientation from AGENTS.md.
---

# Project Context (Compatibility Only)

New tasks must not route through this wrapper. Use the direct task route in `AGENTS.md`, then `context-select.py`, the relevant section of `context-memory.md`, and targeted README / reference / source / test reads.

## Workflow Metadata

| field | value |
|---|---|
| scope | compatibility-only pointer |
| trigger_evidence | an older installed workflow explicitly invokes the legacy skill name |
| negative_trigger | every new task and every current direct-orientation route |
| precedence | none |
| conflicts | none |
| input_budget | <= 120 tokens |
| output_contract | redirect to direct project orientation without loading another workflow layer |
| owner_source | .agents/references/workflow/context-memory.md#Context Selection |
| source_digest | sha256:8f1fafd23e564287c342d50af5137483c9aeb5a42f23c1599b66dfdf795abe46 |
| validation | python3 .agents/scripts/validate-local-skills.py --root . --strict-quality |

## Forbidden Actions

- Do not treat this compatibility file as a Gate, task state, implementation authorization, or reason to scan the repository broadly.
- Do not copy project facts into this file.

## Validation

- Confirm that new routes do not return this Skill and that direct orientation still finds relevant conventions, known-bad paths, source, tests, and verification entry points.

## References Boundary

- Current orientation is owned by `AGENTS.md` and `.agents/references/workflow/context-memory.md#Context Selection`.
- This file may be removed only when installed-package cleanup can remove stale Skill files safely.
