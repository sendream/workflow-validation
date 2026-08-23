# Role Review Packet

> Template file: `.agents/templates/role-review-packet.md`.
> Generated packet file: `.agent-state/runs/<run_id>/role-review/<role>/review-packet.md`, or `.agent-state/runs/<run_id>/multi-agent-campaign/role-review/<role>/review-packet.md` inside a campaign.
> Legacy `.agent-state/runs/<run_id>/isolated-review/` packets are read-only compatibility inputs only. Generated packets are bounded read-only review artifacts, not project state sources. Use `.agents/scripts/validate-role-review-packet.py --strict` or `--risk-tier high|release` for high-risk review packets.

## Pre-start Boundary
Create this packet only for a reviewer path that will validate a packet before start, including a typed invalid-packet path. A clean assessment-only / not-needed decision does not create a packet; record the existing compact assessment in `progress.md` instead:

| item | value |
|---|---|
| Required assessment | yes |
| Trigger decision | assessment-only / not-needed |
| Reason | concrete non-start reason |
| Authorization scope | none |
| Start required | no |
| Start result | not-needed |

Reviewer tool, runtime policy, packet, budget, verdict, and fallback are conditional startup or exceptional-path fields. Do not add them to this compact path merely to fill a template; fallback remains required for unavailable / incomplete / invalid / denied paths.

## Task
- Risk Tier:
- Impact Scope:
- Goal:
- Negative Constraints:

## Agent Brief
Agent Brief is the task contract for the reviewer. Reviewer Policy below is the permission contract.

| field | value |
|---|---|
| role | requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed |
| task_class | exploration / review / verification / handoff |
| goal | one concrete submitted claim this reviewer should try to falsify |
| context | short task background; do not include full chat history |
| ownership | finding-only / no-state-ownership |
| output_format | falsification_attempts with hypothesis, probe, evidence, outcome; findings table with severity, evidence_level, linked_acceptance_id, linked_scenario_id, linked_slice_id, case_class, evidence, recommended_disposition |
| stop_condition | max files 12; max time 20 minutes; max findings 10; before pass record at least one executable falsification attempt; stop if packet insufficient or no executable probe exists; stop if secrets are suspected |

## Review Scope
- Review focus: quality / security / test-coverage / release-risk / knowledge-promotion / mixed
- Files to review:
- Explicitly out of scope:
- Focus notes:

## Reviewer Policy
| field | value |
|---|---|
| repo_write_scope | none |
| artifact_write_scope | none / result-artifact-only-under-packet |
| allowed_actions | read, rg, git diff, git status |
| prohibited_actions | repo write, source write, edit, task_plan, progress, findings, source changes, deploy, db write, commit, push, secrets, new state source |
| state_source_policy | no second state source; packet-and-result-are-artifacts-not-project-state; findings only, main Codex writes disposition |
| subdelegation | none |

## Reviewer Execution Metadata
This section is conditional on packet validation or startup. It is not part of the compact non-start record above.

| field | value |
|---|---|
| reviewer_tool | Codex subagent / Gemini / Claude / other / unavailable / runtime-policy-blocked |
| runtime_policy_status | not-checked / allowed / runtime-policy-blocked / explicit-delegation-required / explicit-denied / revoked / not-needed |
| agent_type | explorer / not-needed |
| review_engine_policy | inherit-primary / native-tool-managed / external-reviewer / explicit-approved / not-needed |
| review_engine | inherited primary engine / native review engine / external reviewer engine / explicit approved engine / not-needed |
| review_reasoning_tier | high-assurance-review / reduced:budget-capped / reduced:unsupported / exceptional:explicit-budget+quality-priority / tool-managed / not-needed |
| budget | file scope + time/token limit / 待填写 |
| runtime_enforced_budget | hard-timeout / hard-turn-limit / hard-file-limit / prompt-soft-limit / manual-fallback / not-needed |
| timeout_policy | review-incomplete / reviewer-timeout; do not rely on interrupt context recovery |
| prompt_policy | short self-contained prompt with review questions, scope, output contract, and budget |

These three review-engine fields are tool-neutral. `high-assurance-review` means the tool's explicitly mapped highest regular deep-review tier, not a newly available exceptional premium tier. For Codex, inheriting the primary model and using `reasoning_effort: xhigh` for high / release / external-system review is one mapping example, not a portable parameter contract. A lower tier records `budget-capped` or `unsupported`; an exceptional tier requires both an explicit budget and `quality-priority=yes`.

## Inputs
- Diff: `diff.patch`
- Changed files: `changed-files.txt`
- Evidence ledger: `evidence-ledger.md`
- Waivers: `waivers.md`
- Dirty worktree summary: `dirty-worktree-summary.json`
- Release-source summary: not-needed / path
- Scenario snapshot: not-needed / `role-review-scenario-packet.md`

## Review Evidence Index
Every high / release review packet should link reviewer claims to raw, replayable evidence rather than pass summaries. Light reviewer packets may omit this table unless `--strict` / `--risk-tier high|release` is used.

| check_id | command | exit_code | status | artifact_path | stdout_stderr_summary_path | run_id | timestamp | waiver_id |
|---|---|---|---|---|---|---|---|---|
| C1 | command / not-run | 0 / nonzero / not-run | PASS / FAILED / WAIVED / BLOCKED / NOT_APPLICABLE | `.agent-state/runs/<run_id>/...` / not-needed | `.agent-state/runs/<run_id>/...` / manual-note / not-needed | `<run_id>` | ISO-8601 / 待填写 | WAIVER-... / not-needed |

## Reviewer Task
Only review. Use an evidence-neutral, falsification-first posture: test the submitted claim rather than seeking confirmation. Do not modify files, deploy, push, access secrets, create a new plan, or create a second progress system. If the review cannot complete within budget, return `review-incomplete` with evidence checked and missing evidence; do not wait for an interrupt to reconstruct the task.

## Output Contract
If artifact capture is supported, place the machine-readable reviewer result at `role-review-result.json` under the packet directory only; otherwise return the same fields in Markdown and let main Codex transcribe disposition into `progress.md`.
If `progress.md` records `policy-auto-started`, `task-authorized-started`, `session-authorized-started`, or `external-opt-in-started`, strict closeout requires `role-review-result.json` under the packet directory. If no result artifact can be captured, record `review-incomplete`, `reviewer-timeout`, or the typed non-start reason instead of a started result.

For `verdict=pass`, `role-review-result.json` must contain a non-empty `falsification_attempts` list. Each attempt is an object with these non-placeholder fields:
- `hypothesis`: the submitted claim or failure hypothesis tested
- `probe`: the concrete falsification action performed
- `evidence`: a declared check id, packet file, or artifact path that can be replayed
- `outcome`: `excluded / not-reproduced / not-applicable`

The attempts for a pass cannot all be `not-applicable`; use `review-incomplete` when no executable probe can be formed. A non-pass verdict does not require `falsification_attempts`. A failed falsification attempt is useful evidence and does not need to manufacture a finding.

Each finding must include:
- finding_id
- severity: S0 / S1 / S2 / S3
- evidence_level: direct / indirect / unverified
- linked_acceptance_id
- linked_scenario_id
- linked_slice_id
- case_class
- claim
- evidence
- recommended_disposition
