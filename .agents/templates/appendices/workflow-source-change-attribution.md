# Progress Appendix: Workflow-Source Change Attribution

> Optional appendix for workflow-source changes only. Derived planning evidence, not task state, not a runner, not delivery approval, and not required for ordinary business tasks.

Use this appendix when editing workflow rules, validators, evals, reports, templates, skills, or starter-pack scripts where a changed file should be tied to a stable harness component.

## Workflow-Source Change Attribution
| path | type | reason | component_id | change_type | validation_gate | reward_hacking_review | rollback_plan |
|---|---|---|---|---|---|---|---|
| `path/to/file` | docs / validator / eval / report / template / script | concise reason | `component-id` / not-needed | add / narrow / relax / remove / refactor | smoke / behavior-eval / validator / not-needed | positive+negative+boundary / not-needed | revert file / revert fixture / not-needed |

## Rules
- `component_id` must match `.agents/references/harness-components.md` when the change affects a registered harness mechanism.
- Use `not-needed` for pure wording, typo, formatting, or repository-maintenance changes.
- Do not place command strings, deploy instructions, credentials, raw logs, private paths, expected held-out answers, or runtime state in this appendix.
- `reward_hacking_review` should name the coverage shape, not a score. Valid examples: `positive+negative+boundary`, `no-trigger-fixture`, `public-benchmark-not-held-out`, `not-needed`.
- This appendix does not authorize reviewer startup, plugin/MCP enablement, deploy, push, DB writes, external writes, or skill/global workflow changes.

## Workflow Evolution Decision
| candidate_id | component_id | candidate_sha256 | decision | evidence_chain | decision_evidence | rollback_plan | adopted_state_ref | adopted_state_sha256 | rollback_target_ref | rollback_target_sha256 |
|---|---|---|---|---|---|---|---|---|---|---|
| `HC-...` | `component-id` | 64-hex digest of the bounded candidate artifact | adopt / rollback / reject / defer | `.agent-state/runs/<run_id>/harness-evolution/evolution-chain.json` | bounded validation and review evidence | revert bounded patch / restore prior trigger | adoption record / not-needed | 64-hex / not-needed | prior-state artifact / not-needed | 64-hex / not-needed |

Schema v2 binds the compared incumbent plus an acceptance report recomputed from the proposer contract and separately stored result artifacts. The static validator can report `trial-eligible` or `paired-evidence-complete`, but it always records `execution_isolation_verified=false` and `adoption_eligible=false`; those artifacts cannot support `adopt`. Independent execution evidence remains an explicit external experiment, and this table cannot override that missing proof.

### Evolution decision rules
- This progress row is the decision authority. The JSON chain and run manifests are derived evidence only.
- `adopt` requires matching current validation and pilot run manifests. Each outcome run must include a command-produced `workflow-candidate-evaluation` result bound by digest; candidate argv presence alone is insufficient.
- `rollback` additionally requires a structured adoption record, a digest-bound rollback target, and a passing rollback-check manifest that evaluates the restored target.
- `reject` requires failed or blocked matching validation evidence. `defer` may preserve the candidate without running it.
- `candidate_ref` must stay under the chain's `harness-evolution/` directory. The progress row, chain, and every run manifest must bind the same `candidate_sha256`.
- All run manifests must carry the same `candidate_id`, `component_id`, candidate/result digests in optional `workflow_attribution`, and use the correct `phase`.
- A private held-out manifest may be referenced as metadata only and must bind to the same candidate/component. It never stores samples or answers and never becomes a default CI or delivery gate.
- The row does not apply a patch, authorize writes, or start a live evaluator. Any workflow-source edit still follows normal user/task authorization.
