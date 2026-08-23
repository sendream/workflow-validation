# Role Review Packet

## Task
- Risk Tier: high
- Impact Scope: file-linked
- Goal: Falsify the claim that replacement candidate `1ff34455be35812ab10cebd66e6730f68eab1196` removes quadratic formatting work for long monotonic flat ASCII NAME/NUMBER consecutive subscript chains while preserving all existing formatting bytes, including legacy optional-RHS-parenthesis boundaries.
- Negative Constraints: Review only; do not modify repository or workflow state, inspect PR #5275 or #5305 or related artifacts, start another agent, push, commit, or weaken the output-identity contract.

## Candidate Binding
| item | value |
|---|---|
| base revision | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| rejected revision | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6` |
| candidate revision | `1ff34455be35812ab10cebd66e6730f68eab1196` |
| diff artifact | `diff.patch` |
| diff SHA-256 | `3b6650e7561f3ac48c37a14dabb35b9c6654ee7937974c0aa453bdbfb0aff20f` |
| changed-files SHA-256 | `6648f4b18082459f29ea0aca51b153b9a3ff80c1bf974abc3b9e270d2e38bc3b` |
| locked branch | `trial/t3-5270` |

## Agent Brief
| field | value |
|---|---|
| role | qa |
| task_class | review |
| goal | Try to falsify closure of all three accepted findings, output identity, benchmark validity, non-quadratic residual behavior, guard isolation, and regression-test strength for the exact replacement candidate. |
| context | Three prior exact-SHA reviews rejected candidates for annotated NAME drift, increasing-width CJK STRING drift, and an optional-RHS-parenthesis boundary at custom line lengths; a controller probe separately rejected wide CJK NAME acceptance. This candidate accepts only ASCII NAME/NUMBER bodies and additionally fails open when the cumulative width through the RHS base exactly equals the line length. The packet includes a 3,920-case line-length 1..140 scan across seven assignment contexts and four body families. |
| ownership | finding-only |
| output_format | `falsification_attempts` with hypothesis, probe, evidence, outcome; findings with finding_id, severity, evidence_level, linked_acceptance_id, linked_scenario_id, linked_slice_id, case_class, claim, evidence, recommended_disposition. |
| stop_condition | Max files 12; max time 20 minutes; max findings 10; before pass record executable falsification attempts; stop with review-incomplete if packet insufficient or no executable probe exists; stop if secrets are suspected. |

## Review Scope
- Review focus: mixed
- Files to review: `CHANGES.md`, `src/black/linegen.py`, `tests/data/cases/long_flat_subscript_chain.py`, `tests/test_format.py`, and the packet evidence files.
- Explicitly out of scope: all other worktrees, trial reports, unrelated trial branches, PR #5275, PR #5305, upstream writes, source edits, workflow edits, and reviewer subdelegation.
- Focus notes: Treat exact formatting bytes as a hard compatibility boundary. Prefer a concrete counterexample or replayable probe over stylistic opinion. The prior blocking result is a required falsification target, not a reason to defer independent re-checking.

## Reviewer Policy
| field | value |
|---|---|
| repo_write_scope | none |
| artifact_write_scope | result-artifact-only-under-packet |
| allowed_actions | read, rg, git diff, git status, and run existing test or benchmark probes |
| prohibited_actions | repo write, source write, edit, task_plan, progress, findings, source changes, deploy, db write, commit, push, secrets, new state source, prohibited PR access |
| state_source_policy | no second state source and no new state source; packet and result are bounded artifacts, and only the main Codex records disposition |
| subdelegation | none |

## Reviewer Execution Metadata
| field | value |
|---|---|
| reviewer_tool | Codex subagent |
| runtime_policy_status | explicit-delegation-required |
| agent_type | explorer |
| review_engine_policy | inherit-primary |
| review_engine | inherited primary engine |
| review_reasoning_tier | high-assurance-review |
| budget | max 12 files; max time 20 minutes; max findings 10 |
| runtime_enforced_budget | prompt-soft-limit |
| timeout_policy | review-incomplete; do not rely on interrupt context recovery |
| prompt_policy | short self-contained prompt with review questions, scope, output contract, and budget |

## Inputs
- Diff: `diff.patch`
- Changed files: `changed-files.txt`
- Evidence ledger: `evidence-ledger.md`
- Waivers: `waivers.md`
- Dirty worktree summary: `dirty-worktree-summary.json`
- Prior rejected-result evidence: sibling packet archives `../qa-d522def/role-review-result.json`, `../qa-5757101/role-review-result.json`, and `../qa-483b25d/role-review-result.json`.
- Release-source summary: no release artifact exists for this source-only patch.
- Scenario snapshot: behavior scenarios S1-S6 and acceptance requirements R1-R7 are reproduced in `evidence-ledger.md`.

## Review Evidence Index
The authoritative C1-C9 table is in `evidence-ledger.md`; every command artifact is local, immutable for this review, and bound to the locked replacement candidate where applicable.

## Reviewer Task
Only review. Use an evidence-neutral, falsification-first posture and bind every conclusion to a declared check, packet file, or replayable artifact.

1. Re-run or independently vary all prior counterexamples. Confirm annotated ASCII NAME assignments match legacy, CJK STRING/CJK NAME chains do not enter the batch path, and the line-length=10/17 optional-parenthesis cases now use legacy.
2. Challenge output identity using C10, C11, and C13. Confirm C11 really compares optimized output with the forced unchanged legacy path for 3,920 cases at every line length 1..140, exercises accepted ASCII NAME/NUMBER shapes in seven assignment contexts, and reports no mismatch. Try to move the exact-prefix failure to a different context or line length.
3. Challenge corpus evidence. Confirm C5 compares all 972 raw baseline fixture-loader invocations, including four duplicate keys, without dictionary collapse; try to find an unmatched baseline entry.
4. Challenge the work oracle and performance protocol. Verify the explicit n80/n160 linear bounds, real `_first_right_hand_split` calls, exact generator/API, warm-up, samples, medians, and C10 n160/n300 scaling.
5. Inspect fallback isolation, atomic-yield behavior, source complexity, and any accepted syntax shape that can still drift. Report direct S0/S1 evidence if found; do not infer PASS from the existing GREEN artifacts alone.

Do not modify files, deploy, push, access secrets, create a plan, create a second progress system, inspect prohibited PR artifacts, or subdelegate. If the review cannot complete within budget, return `review-incomplete` with evidence checked and missing evidence.

## Output Contract
Write only `role-review-result.json` under this packet directory. The result must contain `role`, `verdict`, `summary`, `falsification_attempts`, and `findings`.

For `verdict=pass`, `falsification_attempts` must be non-empty. Every attempt must contain non-placeholder `hypothesis`, `probe`, `evidence`, and `outcome`; `evidence` must name a declared check id, packet file, or replayable artifact; `outcome` must be `excluded`, `not-reproduced`, or `not-applicable`, and the attempts cannot all be `not-applicable`.

Every finding must contain:
- `finding_id`
- `severity`: S0, S1, S2, or S3
- `evidence_level`: direct, indirect, or unverified
- `linked_acceptance_id`
- `linked_scenario_id`
- `linked_slice_id`
- `case_class`
- `claim`
- `evidence`
- `recommended_disposition`

Use `review-incomplete` rather than `pass` if no executable falsification probe can be formed. A pass means only that the declared probes found no material falsifier in scope.
