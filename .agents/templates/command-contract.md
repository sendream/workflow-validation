# Command Contract

> Optional prompt / command contract template. Generated or copied contracts are reference artifacts only: not a runner, not a skill, not a hook, and not a second state source.
> This contract cannot authorize repo-write, external-write, deploy, push, DB write, secrets access, or subagent startup. Those still follow `AGENTS.md`, `workflow-details.md`, `tooling-map.md`, and user authorization rules.

## Contract Metadata
| field | value |
|---|---|
| id | hyphen-case-id |
| kind | prompt-snippet / command-contract / reviewer-prompt / translation-contract |
| status | disabled / trial / available |
| description | one-sentence purpose |
| trigger | explicit user request or narrow repeated task condition |
| non_trigger | fast path / low / unrelated task / private data not authorized / external-write not authorized |
| risk_tier_floor | low / standard / high / release |
| scope | repo-read / report-write-only / implementation-authorized |
| requires_explicit_authorization | yes / no |
| source_of_truth | user prompt / project docs / `.agents/references/...` / not-needed |
| refresh_when | input format, output format, permissions, or project terminology changes |

## Permissions
| field | value |
|---|---|
| repo_read | yes / no |
| repo_write | yes / no |
| external_read | yes / no |
| external_write | yes / no |
| network | none / loopback / internet / internal |

## Inputs
- user_args
- explicit_files
- existing evidence artifact / not-needed

## Forbidden
- Do not run inline shell expansion such as `!cmd`.
- Do not infer commit history, external account data, or private context unless explicitly provided.
- Do not commit, push, deploy, write DB data, access secrets, or create a second plan/progress system.
- Do not bypass `tooling-map.md` or `tooling-router.py` for deterministic tools.

## Outputs
| field | value |
|---|---|
| final_response | summary + risks + verification / not-needed |
| artifacts_allowed | `.agent-state/runs/<run_id>/...` / user-approved report path / none |
| evidence_binding | command / artifact / source excerpt / not-needed |

## Trigger Eval
| case | prompt |
|---|---|
| positive | 待填写 |
| negative | 待填写 |

## Collision Check
- Does not replace `requirements-to-plan`.
- Does not replace the active three-file state contract.
- Does not replace `tooling-router`.
- Does not create a second task state source.
