# Command Catalog

> Optional reference only. This catalog is not a runner, not a skill, not a hook input, and not a second state source.
> Use it only when the user explicitly asks for a repo-local prompt / command contract, or when a project has already adopted one for a narrow repeated task.

## Purpose
Record reusable prompt snippets and command contracts with explicit triggers, permissions, inputs, forbidden actions, outputs, and collision checks.

This file does not authorize:
- repo writes
- external writes
- deploy / push / DB operations
- subagent startup
- inline shell expansion
- bypassing `tooling-map.md`, `tooling-router.py`, `task_plan.md`, `progress.md`, or `findings.md`

If a contract needs a deterministic tool, reference a tool class from `tooling-map.md`; do not duplicate command routing here.

## Use Rules
- `prompt-snippet`: text guidance only; it cannot authorize tool calls or file writes.
- `command-contract`: a structured task contract; it can describe inputs and outputs, but execution still follows normal workflow gates.
- `reviewer-prompt`: reviewer packet prompt helper; it must preserve Agent Brief / Reviewer Policy boundaries.
- `translation-contract`: terminology-sensitive text transformation; read `terminology.md` first when relevant.
- Default status for new entries is `disabled` or `trial`; use `available` only after the trigger and negative trigger have been validated.
- Do not add `required` status. Required behavior belongs in `AGENTS.md`, `workflow-details.md`, a validator, or a project test.

## Catalog
| id | kind | status | trigger | contract_path | notes |
|---|---|---|---|---|---|
| not-needed | prompt-snippet / command-contract / reviewer-prompt / translation-contract | disabled / trial / available | 待填写 | `.agents/templates/command-contract.md` / `.agents/references/commands/<id>.md` | 待填写 |

## Validation
Run after adding or changing command contracts:

```sh
.agents/scripts/validate-command-catalog.py --root . --catalog .agents/references/command-catalog.md --contract .agents/references/commands/<id>.md --format json
```

The validator is structural only. It does not execute commands, start reviewers, or judge content quality.
