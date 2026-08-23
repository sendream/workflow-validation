# Role Review Scenario Packet

> This is a read-only review packet / snapshot template, not a project state source.
> Authoritative source: `task_plan.md` -> `Behavior Scenarios`, `Example Table`, and `Interface / Domain Contract Delta`.
> Generated copies must live under `.agent-state/runs/<run_id>/role-review/<role>/` and must not be edited as a second behavior contract.

## Snapshot Metadata
| field | value |
|---|---|
| generated_at | ISO-8601 / 待填写 |
| source_file | `task_plan.md` |
| source_section | Behavior Scenarios / Example Table / Interface / Domain Contract Delta |
| source_commit_or_worktree_state | commit SHA / dirty worktree summary path / 待填写 |
| source_sha256 | 64-hex sha256 of source excerpt / 待填写 |
| generated_by | main Codex / tooling / 待填写 |
| readonly_snapshot | true |
| authoritative_source | `task_plan.md` |

## Behavior Scenarios
| scenario_id | actor / context | given / state | when / action | then / observable outcome | negative / boundary | acceptance_id | test layer | evidence method | status |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 待填写 | 待填写 | 待填写 | API response / UI state / permission denial / artifact / audit log | none / 待填写 | A1 | unit / service / API / browser / manual / release-smoke | command / artifact / screenshot / trace / API response / manual note | pending |

## Example Table
| rule_id | example_id | input / state | expected result | invalid / edge case | source | linked scenario |
|---|---|---|---|---|---|---|
| R1 | E1 | 待填写 | 待填写 | none / 待填写 | user / PRD / existing behavior / code / docs | S1 |

## Interface / Domain Contract Delta
| contract_id | surface | field / operation | old behavior | new behavior | null / empty semantics | compatibility | negative cases | linked scenario |
|---|---|---|---|---|---|---|---|---|
| C1 | API / UI / DB / import-export / permission / external | 待填写 | 待填写 | 待填写 | not-needed / null / empty-string / omitted / 待填写 | compatible / breaking / migration-needed / not-needed | none / 待填写 | S1 |

## Mapping
| acceptance_id | scenario_id | verification | evidence |
|---|---|---|---|
| A1 | S1 | 待填写 | `.agent-state/runs/<run_id>/...` / 待填写 |
