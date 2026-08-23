---
name: requirements-to-plan
description: Compatibility marker for older installs; new tasks write the requirement contract from AGENTS.md and G03.
---

# Requirements To Plan (Compatibility Only)

New tasks must not route through this wrapper. When requirements need a decision-ready contract, follow `AGENTS.md`, G03, and the core `task_plan` fields.

## Workflow Metadata

| field | value |
|---|---|
| scope | compatibility-only pointer |
| trigger_evidence | clarificationcontract g03only |
| negative_trigger | every new task and every current direct-contract route |
| precedence | none |
| conflicts | none |
| input_budget | <= 120 tokens |
| output_contract | redirect to G03 and the core task contract without loading another workflow layer |
| owner_source | .agents/references/workflow/gate-cards.md#G03_CLARIFICATION |
| source_digest | sha256:8430a7bdfd7b7277658e921c39166d3c3748ad9c1d0d5600e47fc75e6657c309 |
| validation | python3 .agents/scripts/validate-local-skills.py --root . --strict-quality |

## Forbidden Actions

- Do not treat this compatibility file as a Gate, task state, or reason to create three files for a fast task.
- Do not copy requirements, acceptance tables, or project facts into this file.

## Validation

- Confirm current routes do not return this Skill and that requirement prompts select G03 instead.
- Run the local Skill validator and the affected deterministic behavior tests after changing this pointer.

## References Boundary

- Requirement contracts are owned by `AGENTS.md`, G03, and core templates.
- This file may be removed only when installed-package cleanup can remove stale Skill files safely.
