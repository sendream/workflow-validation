# Role Review Packet

## Task
- Risk Tier: high
- Impact Scope: file-linked
- Goal: Falsify the claim that candidate `d522defdf8a6ea6858aa0b95b34b31a3865a55c6` removes quadratic formatting work for long flat consecutive subscript chains while preserving all existing formatting bytes.
- Negative Constraints: Review only; do not modify repository or workflow state, inspect PR #5275 or #5305 or related artifacts, start another agent, push, commit, or weaken the output-identity contract.

## Candidate Binding
| item | value |
|---|---|
| base revision | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| candidate revision | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6` |
| diff artifact | `diff.patch` |
| diff SHA-256 | `c0408bf6ec079c040a5ce266f243a07fee0aaf213c93428177f37d3dbb6a5b51` |
| changed-files SHA-256 | `6648f4b18082459f29ea0aca51b153b9a3ff80c1bf974abc3b9e270d2e38bc3b` |
| locked branch | `trial/t3-5270` |

## Agent Brief
| field | value |
|---|---|
| role | qa |
| task_class | review |
| goal | Try to falsify output identity, benchmark validity, non-quadratic residual behavior, guard isolation, and regression-test strength for the exact locked candidate. |
| context | Black issue #5270 attributes quadratic behavior to repeated RHS splitting of flat subscript chains. The candidate adds a narrow batch path and a deterministic real-work regression while requiring exact byte stability. |
| ownership | finding-only |
| output_format | `falsification_attempts` with hypothesis, probe, evidence, outcome; findings with finding_id, severity, evidence_level, linked_acceptance_id, linked_scenario_id, linked_slice_id, case_class, claim, evidence, recommended_disposition. |
| stop_condition | Max files 12; max time 20 minutes; max findings 10; before pass record executable falsification attempts; stop with review-incomplete if packet insufficient or no executable probe exists; stop if secrets are suspected. |

## Review Scope
- Review focus: mixed
- Files to review: `CHANGES.md`, `src/black/linegen.py`, `tests/data/cases/long_flat_subscript_chain.py`, `tests/test_format.py`, and the packet evidence files.
- Explicitly out of scope: all other worktrees, trial reports, trial branches, patches, review artifacts, PR #5275, PR #5305, upstream writes, source edits, workflow edits, and reviewer subdelegation.
- Focus notes: Treat exact formatting bytes as a hard compatibility boundary. Prefer a concrete counterexample or replayable probe over stylistic opinion.

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
- Release-source summary: no release artifact exists for this source-only patch.
- Scenario snapshot: behavior scenarios S1-S6 and acceptance requirements R1-R7 are reproduced in `evidence-ledger.md`.

## Review Evidence Index
| check_id | command | exit_code | status | artifact_path | stdout_stderr_summary_path | run_id | timestamp | waiver_id |
|---|---|---:|---|---|---|---|---|---|
| C1 | `/home/lsy/trials/black-run-1/venv/bin/python .agent-state/runs/t3-5270/scripts/evidence_capture.py --phase baseline` | 0 | PASS | `.agent-state/runs/t3-5270/manifest.json` | `.agent-state/runs/t3-5270/outputs/stdout.txt` | `t3-5270` | `2026-08-23T07:34:20Z` | not-needed |
| C2 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 1 | FAILED | `.agent-state/runs/t3-5270/red/t3-5270-red/manifest.json` | `.agent-state/runs/t3-5270/red/t3-5270-red/outputs/stdout.txt` | `t3-5270-red` | `2026-08-23T07:36:07Z` | not-needed |
| C3 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 0 | PASS | `.agent-state/runs/t3-5270/green/t3-5270-green/manifest.json` | `.agent-state/runs/t3-5270/green/t3-5270-green/outputs/stdout.txt` | `t3-5270-green` | `2026-08-23T07:40:21Z` | not-needed |
| C4 | `/home/lsy/trials/black-run-1/venv/bin/python .agent-state/runs/t3-5270/scripts/evidence_capture.py --phase candidate` | 0 | PASS | `.agent-state/runs/t3-5270/candidate/t3-5270-candidate-final/manifest.json` | `.agent-state/runs/t3-5270/candidate/t3-5270-candidate-final/outputs/stdout.txt` | `t3-5270-candidate-final` | `2026-08-23T07:45:13Z` | not-needed |
| C5 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest -n auto` | 0 | PASS | `.agent-state/runs/t3-5270/final/t3-5270-full-suite-final/manifest.json` | `.agent-state/runs/t3-5270/final/t3-5270-full-suite-final/outputs/stdout.txt` | `t3-5270-full-suite-final` | `2026-08-23T07:45:36Z` | not-needed |
| C6 | `git diff --check` | 0 | PASS | `.agent-state/runs/t3-5270/final/t3-5270-diff-check/manifest.json` | `.agent-state/runs/t3-5270/final/t3-5270-diff-check/outputs/stdout.txt` | `t3-5270-diff-check` | `2026-08-23T07:45:48Z` | not-needed |

## Reviewer Task
Only review. Use an evidence-neutral, falsification-first posture and bind every conclusion to a declared check, packet file, or replayable artifact.

1. Challenge output identity. Inspect `diff.patch` for an accepted syntax shape whose batch partitions may differ from repeated legacy RHS splitting; audit C4's full generated-byte, fixture-key, and explicit trailer-boundary comparisons.
2. Challenge benchmark validity. Verify the exact generator, `black.format_str(source, mode=black.Mode())`, CPython 3.12 metadata, no Black cache, documented warm-up, three raw samples per size, median calculation, and baseline/candidate separation in C1 and C4.
3. Challenge residual non-linearity. Compare deterministic real `_first_right_hand_split` counts with n=160 to n=300 growth; if useful, run a read-only alternate simple flat-chain probe near guard and line-length boundaries. Do not edit fixtures.
4. Challenge test weakness. Determine whether the coarse n40/n80 call bound could pass while the relevant algorithm remains quadratic, whether the static oracle is independent enough, and whether fallback shapes are meaningfully protected by guard structure plus corpus/boundary evidence.
5. Report any guard leakage, partial-yield/fallback issue, misleading metric, untested accepted shape, or compatibility drift as a finding with direct evidence when severity is S0/S1.

Do not modify files, deploy, push, access secrets, create a plan, create a second progress system, inspect prohibited PR artifacts, or subdelegate. If the review cannot complete within budget, return `review-incomplete` with evidence checked and missing evidence.

## Output Contract
If artifact capture is supported, write only `role-review-result.json` under this packet directory. Otherwise return the same fields to the controller for capture. The result must contain `verdict`, `summary`, `falsification_attempts`, and `findings`.

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
