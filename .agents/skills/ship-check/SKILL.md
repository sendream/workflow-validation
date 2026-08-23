---
name: ship-check
description: Compatibility marker for older installs; new delivery decisions use G17 and the current contract.
---

# Ship Check (Compatibility Only)

New tasks must not route through this wrapper. When a delivery decision is requested, follow `AGENTS.md` and G17: yes / conditional / no, bound to acceptance and evidence.

## Workflow Metadata

| field | value |
|---|---|
| scope | compatibility-only pointer |
| trigger_evidence | deliveryverdict g17only |
| negative_trigger | every new task and every current direct-delivery route |
| precedence | none |
| conflicts | none |
| input_budget | <= 120 tokens |
| output_contract | redirect to G17 without loading another workflow layer |
| owner_source | .agents/references/workflow/gate-cards.md#G17_SHIP_CHECK |
| source_digest | sha256:8430a7bdfd7b7277658e921c39166d3c3748ad9c1d0d5600e47fc75e6657c309 |
| validation | python3 .agents/scripts/validate-local-skills.py --root . --strict-quality |

## Forbidden Actions

- Do not treat this compatibility file as delivery authorization, a second evidence ledger, or a release Gate.
- Do not copy release packets or project facts into this file.

## Validation

- Confirm current routes do not return this Skill and that release/delivery prompts select G17 instead.
- Run the local Skill validator and the affected deterministic behavior tests after changing this pointer.

## References Boundary

- Delivery recommendations are owned by `AGENTS.md` and G17.
- This file may be removed only when installed-package cleanup can remove stale Skill files safely.
