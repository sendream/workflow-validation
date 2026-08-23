# Task Plan

## Task
Investigate issue #5270 and deliver a non-quadratic fix only if every formatted byte and all behavior outside a proven guard remain unchanged.

## Current phase
- Phase: partial closeout delivered to review remote; awaiting fable5 audit
- Active task id: `t3-5270`
- Source root: `/home/lsy/trials/black-run-1/worktrees/t3-5270`
- Base revision: `868d4efdbcaf4c29387a99ba854be406b1a1ec99`

## Workflow Routing
| item | value |
|---|---|
| Risk Tier | high |
| Impact Scope | file-linked |
| Task path | complex-task path |
| Reason | Core formatter performance fix with strict formatting-stability, corpus-identity, benchmark, review-packet, and commit gates. |

## Requirement Contract
| id | requirement | acceptance | evidence |
|---|---|---|---|
| R1 | Diagnose and guard the flat consecutive-subscript case with a deterministic regression proxy written before production code. | The new test fails on the base revision for excessive real RHS split work, then passes with the same scenario after the fix. | RED/GREEN pytest artifacts under `.agent-state/runs/t3-5270/`. |
| R2 | Improve the exact CPython 3.12 benchmark using `black.format_str`, no cache, one warm-up, three measured samples, and medians for n=40,80,160,300. | n=160 median is at least 10x faster; n=300 growth no longer exhibits the baseline quadratic pattern. | Baseline and candidate benchmark JSON plus raw samples and environment metadata. |
| R3 | Preserve exact generated output for all four benchmark sizes. | Candidate SHA-256, byte count, and bytes match the baseline for n=40,80,160,300. | Generated-output manifests and byte files. |
| R4 | Preserve the existing formatter fixture corpus and full test health. | Every pre-existing fixture output manifest entry is byte-identical; `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest -n auto` passes. | Before/after fixture manifests, comparison artifact, and captured full-suite run. |
| R5 | Preserve fallback behavior outside the proven guard. | Representative attribute/call/non-subscript trailer formatting and guarded boundary cases remain unchanged and pass focused tests. | Existing fixtures plus focused regression/boundary tests and manifest comparison. |
| R6 | Deliver a minimal product-only local commit chain without workflow/evidence files. | The feature commit and reviewer-driven compatibility correction each contain only their concern; the final diff contains the formatter fix, regression tests, static fixture, and justified `CHANGES.md` entry; overlay and `git diff --check` gates pass. | Final diff, dirty classifier, overlay checks, and commit SHAs. |
| R7 | Run the user-authorized falsification-first read-only Role Reviewer and disposition every finding before delivery. | The packet binds the exact candidate revision/diff/evidence, sets `subdelegation=none`, the result passes the high-risk packet validator, and no accepted blocking finding remains unresolved. | `.agent-state/runs/t3-5270/role-review/qa/` plus the durable finding/disposition rows in `findings.md` and `progress.md`. |

## Scope
- In scope: `src/black/linegen.py`; a focused formatter regression test and/or static case fixture; local evidence artifacts; the required root workflow files; `CHANGES.md` only if Black's conventions require news for an output-identical performance fix.
- Out of scope: formatting-policy changes; broad line-splitting refactors; cache changes; changes to non-subscript trailers; upstream writes or pre-lock inspection of PRs #5275/#5305; push, PR, upstream comment, workflow-source edits.
- Expected final product file count: 0; the attempted four-file product change was reverted after blocking falsification.
- Scope brake: pause before touching any additional product module or weakening output identity/performance/test requirements.

## Negative Constraints
- Do not change a single generated output byte for n=40,80,160,300.
- Do not change any pre-existing formatting fixture output byte.
- Do not route attribute, call, commented, nested, delimited, or otherwise non-proven trailer shapes through the batch path.
- Do not replace deterministic work evidence with a flaky timing assertion.
- Do not inspect PRs #5275/#5305 or their artifacts before the local patch is locked; afterward, comparison is read-only and cannot retroactively support independence.
- Do not exceed one reviewer slot or allow reviewer subdelegation; the controller owns launch and disposition.
- Do not commit `task_plan.md`, `findings.md`, `progress.md`, `.agents/`, `.agent-state/`, `.codex/`, or trial artifacts.
- Do not push to Black upstream, open an upstream PR, comment upstream, or sacrifice output identity for speed. The user-authorized review repository is the only delivery remote.

## Verification Matrix
| acceptance / risk | scenario_id | case_class | evidence method | required checks | test oracle / independence | blocking | evidence |
|---|---|---|---|---|---|---|---|
| R1 deterministic algorithmic regression | S1 | property | command + artifact | focused tests RED then GREEN using the same real split-work proxy | pre-fix observed call-count growth and explicit n80/n160 linear bounds independent of candidate code | block | original and reviewer-counterexample RED captured; final diagnostic 90 calls at n80/n160/n300 |
| R2 performance protocol | S1 | property | command + JSON artifact | exact generator; CPython 3.12; warm-up; 3 samples; median at 40/80/160/300 | baseline samples captured before production edit | block | experimental candidate exceeded 10x, but was not deliverable because R3/R5 failed outside the narrow matrix |
| R3 generated byte identity | S2 | compatibility | byte files + SHA-256 manifest | exact equality at all four n values | immutable baseline byte files and hashes | block | comparison PASS for n40/n80/n160/n300 |
| R4 existing fixture-corpus identity | S3 | compatibility | deterministic before/after manifest | every raw baseline loader invocation is multiset-matched without collapsing duplicate keys | Black test loader, fixture flags, and immutable 972-entry baseline manifest | block | zero unmatched baseline entries; four duplicate keys retained |
| R4 full test health | S3 | compatibility | command artifact | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest -n auto` | repository test suite | block | final reverted revision: 481 passed, 3 skipped in 6.77s |
| R5 non-subscript/fallback stability | S4 | boundary | focused tests + corpus manifest + differential matrix | representative boundaries and 162 optimized/forced-legacy shapes remain unchanged | existing expected fixtures, pre-fix outputs, forced unchanged RHS fallback | block | 89 batch-accepted cases, zero mismatches |
| R6 safe delivery | S5 | contract | git/validator commands | product diff must be empty if no candidate meets all blocking requirements | Git history and exact product paths | block | `1ac5227` reverts all experimental product changes; only trial report is deliverable |
| R7 reviewer challenge | S6 | negative | packet/result validator artifacts | strict/high exact-SHA packet and result | installed template and validator | block | strict result contract PASS; verdict blocking with QA-T3-5270-008/009/010 accepted |

## Execution Table
| slice_id | slice_type | files | action | acceptance | verify | done |
|---|---|---|---|---|---|---|
| E1 | risk | root workflow files; `.agent-state/runs/t3-5270/` | Record contracts; capture environment, full baseline timing samples, generated bytes/hashes, and fixture manifest. | R2, R3, R4 | baseline capture manifest and artifact inspection | done |
| E2 | story | `tests/test_format.py`; `tests/data/cases/long_flat_subscript_chain.py` | Add the deterministic work-proxy regression and exact formatting fixture; run it against unmodified production code. | R1, R3 | focused pytest fails only because 1,700 calls exceed 68*4 while bytes match | done |
| E3 | technical | `src/black/linegen.py` | Add the guarded batch partition path using existing bracket line builders; preserve the legacy fallback for all rejected shapes. | R1, R5 | focused GREEN plus boundary tests | done |
| E4 | risk | product files; `.agent-state/runs/t3-5270/` | Re-run exact benchmarks, output hashes, fixture manifest comparison, focused/relevant/full suites, and diff checks. | R2, R3, R4, R5 | all blocking matrix rows green | done |
| E5 | risk | reviewer packet; Git index | Perform local enhanced review; stage only product files; run G20 once; commit; then prepare and validate the controller-owned exact-SHA reviewer packet. | R6, R7 | packet validator, closeout validators, staged checks, local commit SHA | done |
| E6 | defect | `src/black/linegen.py`; `tests/test_format.py`; local evidence; reviewer packet/result | Reproduce accepted drift, narrow the guard, strengthen tests/evidence, and re-review each replacement. | R1-R7 | strict reviewer result plus expanded differential probes | done; final candidate blocked |
| E7 | closeout | product history; trial report | Accept the blocking result, stop the overfit guard loop, revert all product changes, rerun the suite, and deliver a partial report. | R3,R5,R6,R7 | empty net product diff; 481/3 suite; report and stats | done |

## Clarification Check
| question_id | blocking? | question | options with recommended default | answer | landing |
|---|---|---|---|---|---|
| C1 | yes | May the guarded batch design proceed after read-only diagnosis? | A. Proceed with exact guarded design (Recommended) / B. Redesign / C. Stop | A, explicitly approved by user | technical decision, scope, negative constraints, behavior scenarios |

## Behavior Scenarios
| scenario_id | actor / context | given / state | when / action | then / observable outcome | case_class | acceptance_id | test layer | evidence method | status |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Black API caller on CPython 3.12 | exact integer subscript chain generator for n=40,80,160,300 | `black.format_str(source, mode=black.Mode())` runs without cache | output is produced with linearized split work; n=160 is >=10x faster and n=300 loses quadratic growth | property | R1,R2 | integration | deterministic work counter + benchmark JSON | pass |
| S2 | Black API caller | immutable baseline bytes for all four n values and broader accepted contexts | candidate formats the same sources | byte count, SHA-256, and full bytes are identical | compatibility | R3 | integration | byte comparison artifact + reviewer differential probes | blocked for every direct-batching candidate; final product reverted |
| S3 | formatter fixture corpus | all pre-existing cases loaded with Black's loader and declared flags | candidate formats each input | every baseline case key and output hash is unchanged; full suite passes | compatibility | R4 | integration | before/after manifest + pytest | pass |
| S4 | existing formatter users | surrounding assignments, annotations, bases, line lengths, and guard-rejected shapes | candidate formatting runs | legacy formatting output remains byte-identical | boundary | R5 | unit/integration | reviewer and controller differential matrices | blocked; final 625-case probe found 133 mismatches among 239 accepted cases |
| S5 | local delivery | dirty workflow/evidence state plus product patch | product files are staged for one commit | no workflow/evidence/trial file is staged or committed | contract | R6 | command | G20 and staged diff artifacts | pass |
| S6 | controller-owned read-only reviewer | exact narrowed replacement diff and complete deterministic evidence | same qa reviewer challenges the candidate | packet requires fresh falsification and `subdelegation=none` | negative | R7 | command | strict packet/result validator JSON | blocking result accepted |

## Example Table
| example_id | linked_scenario | input / state | case_type | oracle / expected observable | counterexample / negative | covered_by acceptance/risk id | must_verify | notes |
|---|---|---|---|---|---|---|---|---|
| EX40 | S1 | n=40 exact generator | property | candidate bytes equal baseline; measured median recorded | a faster but different bracket layout is failure | R1,R2 | yes | warm-up plus 3 samples |
| EX80 | S1 | n=80 exact generator | property | candidate bytes equal baseline and split-work doubling bound passes | timing-only assertion is not the regression oracle | R1,R2 | yes | deterministic work proxy covers algorithm |
| EX160 | S1 | n=160 exact generator | property | candidate median is at least 10x faster than baseline | 9.99x is failure | R2 | yes | primary speed threshold |
| EX300 | S1 | n=300 exact generator | property | candidate bytes equal baseline and observed growth exponent is below 1.5 | retaining approximately n-squared scaling is failure | R2 | yes | raw samples retained |
| EXTRAILER | S4 | representative attribute/call trailer fixture | boundary | exact pre-fix output retained by legacy path | widening the guard to unrelated trailer chains is failure | R5 | yes | existing-format boundary |

## Interface / Domain Contract Delta
| contract_id | surface | old behavior | new behavior | null / empty semantics | compatibility | negative cases |
|---|---|---|---|---|---|---|
| IC1 | formatter output and runtime work | stable bytes with quadratic split work for long flat consecutive subscripts | identical stable bytes with batched split work only under the proven guard | not-needed | byte-for-byte required | all non-guard shapes retain legacy fallback |

## Defect Closure Criteria
| item | value |
|---|---|
| defect id | `black-5270` |
| reproduction before fix | baseline `.agent-state/runs/t3-5270/manifest.json`; RED `.agent-state/runs/t3-5270/red/t3-5270-red/manifest.json` |
| expected behavior | output-identical formatting with non-quadratic work and required speedup |
| actual behavior | recursive RHS splitting repeatedly rebuilds shrinking prefix lines and retries omission candidates |
| root cause | known; repeated rightmost-bracket fallback on a flat subscript suffix |
| post-fix regression evidence | reviewer-counterexample RED; final candidate comparison; 162-case differential; final 486/3 full-suite manifest |
| closure status | unresolved by this trial; direct-batching candidates failed output identity, all product changes were reverted, and only the partial investigation report is deliverable |

## Affected Source Roots
| root_id | repo_id | source_root | reason | structural_index_provider | evidence expectation |
|---|---|---|---|---|---|
| black-root | psf-black-local | `.` | formatter implementation, tests, local evidence, and product-only commit all belong to this checkout | none | run manifest, source-file diff, test and benchmark artifacts |

## Technical Decision Notes
| item | value |
|---|---|
| Options considered | A. Batch the same repeated RHS partitions with existing builders; B. skip only futile omit attempts but retain quadratic rebuilding; C. change the formatting layout to avoid splitting. |
| Decision | Stop and revert direct batching after repeated exact-SHA falsification; retain the unchanged baseline formatter. |
| Trade-offs | The issue remains quadratic, but Black's byte-stable formatting contract is preserved. The report retains timing, rejected-path, and reviewer evidence for a future semantics-preserving design. |
| User confirmation | confirmed |

## Multi-Agent Planning Challenge
| role | trigger | review_mode | start_intent | handoff_status | packet_intent | challenge question |
|---|---|---|---|---|---|---|
| qa | user-request | explicit-delegation-required | controller-owned; do not start locally | to-progress | planned-under-progress | Can the exact candidate be falsified for output drift, misleading benchmarks, residual non-linearity, or a regression test that merely encodes implementation details? |

## Release / External-System Planning
| item | value |
|---|---|
| release artifact expected | no |
| source mode candidate | not-needed |
| rollback point | local parent commit `868d4efdbcaf4c29387a99ba854be406b1a1ec99`; no destructive rollback command authorized |
| S0/S1 red-team focus | output drift, guard leakage, evidence mismatch, staged workflow files |

## Risks
- The existing layout is unintuitive; batching must reproduce the same partition order, visibility, prefixes, indentation, and comments rather than invent a cleaner layout.
- A broad syntactic predicate could alter attribute/call/mixed/nested/commented chains.
- A call-count test can overfit internals; it will wrap real work, use a coarse algorithmic bound, and be paired with exact fixture output and independent timing evidence.
- Benchmarks can be biased by warm-up, cache, interpreter, or sample selection; the protocol and raw samples are fixed in the contract.
