# Progress

## Current Status
- Current phase: partial closeout pushed to review remote; awaiting fable5 audit
- Active task id: `t3-5270`
- Lifecycle state: ready-to-submit-partial
- Archive status: archive-deferred; retain root state and evidence for controller-owned review
- Template scale: full
- Current focus: preserve the frozen partial outcome while fable5 audits `fb0e0fe`
- Next Action: no further product or report edits unless review returns a supported finding
- Blocked By: no product fix meets both performance and byte-identity contracts; this blocks fix delivery but not partial-report delivery

## Source Roots / Repos Touched
| root_id | repo identity | absolute source root | revision / state | evidence scope |
|---|---|---|---|---|
| black-root | current checkout on `trial/t3-5270` | `/home/lsy/trials/black-run-1/worktrees/t3-5270` | replacement candidate `1ff34455be35812ab10cebd66e6730f68eab1196`; rejected `d522def`, `5757101`, `4af4863`, and `483b25d`; base `868d4efdbcaf4c29387a99ba854be406b1a1ec99` | source, tests, benchmark, duplicate-safe fixture manifest, review, Git delivery facts |

## Changed Files Manifest
| path | type | reason |
|---|---|---|
| `task_plan.md` | workflow | required high-risk active contract; never commit |
| `findings.md` | workflow | required diagnosis and decision ledger; never commit |
| `progress.md` | workflow | required evidence and handoff ledger; never commit |
| `.agent-state/runs/t3-5270/` | generated | raw local evidence and reviewer packet; never commit |
| `src/black/linegen.py` | source | experimental changes reverted; final bytes equal task base |
| `tests/test_format.py` | test | experimental changes reverted; final bytes equal task base |
| `tests/data/cases/long_flat_subscript_chain.py` | test | experimental file removed by the explicit revert |
| `CHANGES.md` | docs | experimental entry reverted |
| `trial-reports/t3-5270-report.md` | report | durable partial-outcome and workflow trial record for fable5 review |

## Validation
| command | exit_code | result | artifact |
|---|---:|---|---|
| first controlled baseline capture attempt | 1 | fail | `.agent-state/runs/t3-5270/manifest.json`; import-path harness failure before benchmark execution |
| controlled baseline benchmark/output/fixture capture retry | 0 | pass | `.agent-state/runs/t3-5270/manifest.json`; raw artifacts under `baseline/` |
| `env -u NO_COLOR ... python -m pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 1 | fail | `.agent-state/runs/t3-5270-red/manifest.json`; expected RED: 1,700 > 68*4 |
| same focused regression after production edit | 0 | pass | `.agent-state/runs/t3-5270-green/manifest.json` |
| final exact benchmark/output/fixture/boundary comparison | 0 | pass | `.agent-state/runs/t3-5270-candidate-final/manifest.json`; raw artifacts remain under `.agent-state/runs/t3-5270/candidate/` |
| `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest -n auto` | 0 | pass | `.agent-state/runs/t3-5270-full-suite-final/manifest.json`; 483 passed, 3 skipped |
| `/home/lsy/trials/black-run-1/venv/bin/python -m black --check src/black/linegen.py tests/test_format.py` | 0 | pass | `.agent-state/runs/t3-5270-black-check/manifest.json`; files unchanged |
| `/home/lsy/trials/black-run-1/venv/bin/python -m ruff ...` | 1 | fail | optional tool unavailable; `No module named ruff`; not used as PASS evidence |
| `git diff --check` | 0 | pass | `.agent-state/runs/t3-5270-diff-check/manifest.json` |
| `git check-ignore --no-index -v AGENTS.md .agents .codex` | 0 | pass | terminal output; each path resolves to the shared repository's `.git/info/exclude` |
| full and `--staged-only` dirty classifiers | 0 | pass | exactly four source/doc entries; zero workflow, generated, sensitive, large, or unknown entries |
| G20 staged overlay validator, run once | 1 | adjudicated false positive | `.agent-state/runs/t3-5270-g20/manifest.json`; linked-worktree local-exclude detection only, no staged workflow entries |
| `git -c user.name=Codex -c user.email=codex@openai.com commit -m "Improve flat subscript chain performance"` | 0 | pass | product-only commit `d522defdf8a6ea6858aa0b95b34b31a3865a55c6` |
| high-risk Role Review Packet validator | 0 | pass | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json`; reviewer not launched |
| strict high-risk task closeout | 0 | pass | `.agent-state/runs/t3-5270-closeout/manifest.json`; all fact-domain checks pass with no warnings |
| first isolated qa result for `d522def` | 0 | blocking | archived under `.agent-state/runs/t3-5270/role-review/qa-d522def/`; three accepted findings |
| reviewer counterexample plus strengthened work oracle | 1 | expected RED | `.agent-state/runs/t3-5270-reviewer-red/manifest.json`; annotated output mismatch reproduced |
| final exact benchmark/output/duplicate-safe corpus/boundary comparison | 0 | pass | `.agent-state/runs/t3-5270-candidate-final-v2/manifest.json`; n160 66.34x, exponent 0.854, zero unmatched baseline entries |
| 162-case optimized-versus-forced-legacy differential | 0 | pass | `.agent-state/runs/t3-5270-legacy-differential-v2/manifest.json`; 89 batch-accepted cases, zero mismatch |
| final full suite on `5757101` | 0 | pass | `.agent-state/runs/t3-5270-full-suite-final-v2/manifest.json`; 486 passed, 3 skipped |
| final product Black check | 0 | pass | `.agent-state/runs/t3-5270-black-check-v2/manifest.json` |
| final base-to-candidate diff check | 0 | pass | `.agent-state/runs/t3-5270-diff-check-v2/manifest.json` |
| replacement exact-SHA packet validator | 0 | pass | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json`; reviewer running |
| second isolated qa result for `5757101` | 0 | blocking | archived under `.agent-state/runs/t3-5270/role-review/qa-5757101/`; CJK STRING drift plus missing guard oracle accepted |
| reviewer CJK counterexample and guard-boundary test | 1 / 0 | expected RED then pass | `.agent-state/runs/t3-5270-reviewer-red-v2/manifest.json`; `.agent-state/runs/t3-5270-reviewer-green-v2/manifest.json` |
| final exact benchmark/output/duplicate-safe corpus comparison after STRING exclusion | 0 | pass | `.agent-state/runs/t3-5270-candidate-final-v3/manifest.json`; n160 67.79x, exponent 0.780, zero unmatched baseline entries |
| expanded 258-case optimized-versus-forced-legacy differential | 0 | pass | `.agent-state/runs/t3-5270-legacy-differential-v3/manifest.json`; 86 accepted NAME/NUMBER cases, zero mismatch; STRING cases use legacy |
| final full suite on `4af4863` | 0 | pass | `.agent-state/runs/t3-5270-full-suite-final-v3/manifest.json`; 488 passed, 3 skipped |
| final Black and diff checks on `4af4863` | 0 | pass | `.agent-state/runs/t3-5270-black-check-v3/manifest.json`; `.agent-state/runs/t3-5270-diff-check-v3/manifest.json` |
| narrowed replacement exact-SHA packet validator | 0 | pass | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json`; same qa reviewer running |
| controller wide-NAME guard probe | 1 / 0 | expected RED then pass | `.agent-state/runs/t3-5270-wide-name-red/manifest.json`; `.agent-state/runs/t3-5270-wide-name-green/manifest.json` |
| final exact benchmark/output/duplicate-safe corpus comparison after ASCII narrowing | 0 | pass | `.agent-state/runs/t3-5270-candidate-final-v4/manifest.json`; n160 57.25x, exponent 0.593, zero unmatched baseline entries |
| expanded 290-case optimized-versus-forced-legacy differential | 0 | pass | `.agent-state/runs/t3-5270-legacy-differential-v4/manifest.json`; 86 accepted ASCII NAME/NUMBER cases, zero mismatch |
| final full suite on `483b25d` | 0 | pass | `.agent-state/runs/t3-5270-full-suite-final-v4/manifest.json`; 489 passed, 3 skipped |
| final Black and diff checks on `483b25d` | 0 | pass | `.agent-state/runs/t3-5270-black-check-v4/manifest.json`; `.agent-state/runs/t3-5270-diff-check-v4/manifest.json` |
| final exact-SHA packet validator for `483b25d` | 0 | pass | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json`; same qa reviewer pending |
| third isolated qa result for `483b25d` | 0 | blocking | archived under `.agent-state/runs/t3-5270/role-review/qa-483b25d/`; optional RHS parenthesis boundary accepted |
| default-88 optional-parenthesis boundary test | 1 / 0 | expected RED then pass | `.agent-state/runs/t3-5270-optional-paren-red/manifest.json`; `.agent-state/runs/t3-5270-optional-paren-green/manifest.json` |
| exhaustive line-length 1..140 scan | 1 / 0 | expected RED then pass | before: 8 mismatches / 3,920; after: 0 mismatches / 3,920 in `.agent-state/runs/t3-5270-line-length-scan-green/manifest.json` |
| final exact benchmark/output/duplicate-safe corpus comparison after exact-prefix fallback | 0 | pass | `.agent-state/runs/t3-5270-candidate-final-v5/manifest.json`; n160 60.71x, exponent 0.812, zero unmatched baseline entries |
| final full suite on `1ff3445` | 0 | pass | `.agent-state/runs/t3-5270-full-suite-final-v5/manifest.json`; 490 passed, 3 skipped |
| final Black and diff checks on `1ff3445` | 0 | pass | `.agent-state/runs/t3-5270-black-check-v5/manifest.json`; `.agent-state/runs/t3-5270-diff-check-v5/manifest.json` |
| final exact-SHA packet validator for `1ff3445` | 0 | pass | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json`; same qa reviewer pending |
| strict result validation for `1ff3445` | 0 | blocking result valid | `.agent-state/runs/t3-5270/role-review/qa/role-review-result.json`; QA-T3-5270-008/009/010 accepted |
| final 625-case LHS/base-width differential | 1 | stop signal | 239 accepted cases, 133 byte mismatches; direct batching rejected |
| product diff after `1ac5227` | 0 | pass | `git diff --exit-code 868d4ef..1ac5227 -- CHANGES.md src tests`; empty |
| final full suite after product reversion | 0 | pass | terminal capture; 481 passed, 3 skipped in 6.77s |

## Acceptance Evidence
| acceptance_id | scenario_id | evidence | status | notes |
|---|---|---|---|---|
| R1 | S1 | original RED plus real split-call measurements | PASS for diagnosis | Defect reproduced deterministically; regression was not retained because no safe fix survived. |
| R2 | S1 | baseline/candidate raw samples and comparison | PASS experimentally | Direct batching exceeded 10x, but cannot support delivery without R3/R5. |
| R3 | S2 | reviewer and controller differential probes | BLOCKED | Required four generated cases matched, but broader accepted contexts changed bytes. |
| R4 | S3 | duplicate-preserving corpus evidence; final reverted full suite 481/3 | PASS for final safe state | Corpus/full suite were insufficient to approve candidates but final baseline health is green. |
| R5 | S4 | exact-SHA reviewer probes plus 625-case final matrix | BLOCKED | 133 mismatches among 239 accepted cases. |
| R6 | S5 | empty product diff after `1ac5227` | PASS for partial report | No unsafe product code remains. |
| R7 | S6 | exact-SHA packet and strict result | PASS as governance outcome | `subdelegation=none`; valid blocking result accepted, not rewritten to pass. |

## Diff-to-Plan
| check | status | evidence / notes |
|---|---|---|
| changed files match Scope | pass | Exactly the planned source, focused test, static fixture, and Performance news entry are committed. |
| Negative Constraints respected | pass | No pre-lock PR/artifact access, subdelegation, upstream write, delivered output drift, or workflow/evidence commit occurred; the user-authorized controller launched exactly one reviewer slot. |
| unexpected files explained | not-needed | none observed |

## Run Evidence
| run_id | tool / command | manifest / artifact | status | notes |
|---|---|---|---|---|
| `t3-5270` | baseline evidence capture | `.agent-state/runs/t3-5270/manifest.json` | pass | CPython 3.12 protocol, 4 sizes, 3 samples, exact bytes, 972 fixture entries, boundary outputs |
| `t3-5270-red` | focused pytest RED | `.agent-state/runs/t3-5270-red/manifest.json` | fail | expected TDD RED: output matched but 1,700 real RHS calls exceeded 68*4; byte-identical compatibility copy of nested raw run |
| `t3-5270-green` | focused pytest GREEN | `.agent-state/runs/t3-5270-green/manifest.json` | pass | exact output and deterministic work bound; byte-identical compatibility copy of nested raw run |
| `t3-5270-candidate-final` | exact benchmark/output/fixture/boundary comparison | `.agent-state/runs/t3-5270-candidate-final/manifest.json` | pass | 84.14x n160; exponent 0.779; all identities true; byte-identical compatibility copy of nested raw run |
| `t3-5270-full-suite-final` | required full pytest | `.agent-state/runs/t3-5270-full-suite-final/manifest.json` | pass | 483 passed, 3 skipped; byte-identical compatibility copy of nested raw run |
| `t3-5270-diff-check` | `git diff --check` | `.agent-state/runs/t3-5270-diff-check/manifest.json` | pass | no whitespace errors; byte-identical compatibility copy of nested raw run |
| `t3-5270-black-check` | Black format check | `.agent-state/runs/t3-5270-black-check/manifest.json` | pass | locked product source and focused test unchanged |
| `t3-5270-g20` | staged overlay validator | `.agent-state/runs/t3-5270-g20/manifest.json` | adjudicated | known linked-worktree local-exclude false positive; no staged workflow entries; independent `git check-ignore --no-index` passed |
| not-needed | high-risk packet validation | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json` | pass | packet artifact, not a top-level command run; binds base, candidate SHA, diff hash, product hashes, raw evidence, and required falsification targets |
| `t3-5270-closeout` | strict G21 closeout | `.agent-state/runs/t3-5270-closeout/manifest.json` | pass | all closeout checks and referenced run/packet validators pass with no warnings |
| `t3-5270-candidate-final-v5` | final benchmark/output/fixture/boundary comparison | `.agent-state/runs/t3-5270-candidate-final-v5/manifest.json` | pass | locked `1ff3445`; 60.71x n160, exponent 0.812, exact generated/corpus/boundary identity |
| `t3-5270-line-length-scan-green` | exhaustive optimized-versus-legacy boundary scan | `.agent-state/runs/t3-5270-line-length-scan-green/manifest.json` | pass | 3,920 cases, 1,216 batch acceptances, zero mismatches |
| `t3-5270-full-suite-final-v5` | required full pytest | `.agent-state/runs/t3-5270-full-suite-final-v5/manifest.json` | pass | 490 passed, 3 skipped |
| `t3-5270-black-check-v5` | final Black check | `.agent-state/runs/t3-5270-black-check-v5/manifest.json` | pass | locked product source and focused test unchanged |
| `t3-5270-diff-check-v5` | final base-to-candidate diff check | `.agent-state/runs/t3-5270-diff-check-v5/manifest.json` | pass | no whitespace errors |

## Verification Waivers
| waiver_id | verification | reason | substitute evidence | owner / follow-up | status |
|---|---|---|---|---|---|
| not-needed | none | no waiver requested or permitted for binding output/performance/full-suite requirements | not-needed | main Codex | accepted |

## Final Evidence Ledger
| acceptance id | scenario id | case class | matrix status | supplemental evidence | final status | artifact | notes |
|---|---|---|---|---|---|---|---|
| R1 | S1 | property | PASS | RED `.agent-state/runs/t3-5270-red/manifest.json` | PASS | `.agent-state/runs/t3-5270-green/manifest.json` | Same test failed then passed for intended work assertion. |
| R2 | S1 | property | PASS | baseline `.agent-state/runs/t3-5270/manifest.json` | PASS | `.agent-state/runs/t3-5270-candidate-final-v5/manifest.json` | n160 60.71x; observed exponent 0.812. |
| R3 | S2 | compatibility | PASS | immutable baseline bytes | PASS | `.agent-state/runs/t3-5270/candidate/candidate-comparison.json` | Four exact byte comparisons true. |
| R4 | S3 | compatibility | PASS | duplicate-safe fixture comparison plus full suite | PASS | `.agent-state/runs/t3-5270-full-suite-final-v5/manifest.json` | No pre-existing fixture drift; 490 passed, 3 skipped. |
| R5 | S4 | boundary | PASS | exhaustive candidate-versus-legacy comparison | PASS | `.agent-state/runs/t3-5270-line-length-scan-green/manifest.json` | 3,920 cases at line lengths 1..140; zero mismatch. |
| R6 | S5 | contract | PASS | independent ignore resolution and clean staged classification | PASS | `.agent-state/runs/t3-5270-g20/manifest.json` | G20's linked-worktree exclude warning is adjudicated; staged set is four product files only. |
| R7 | S6 | negative | PASS | exact candidate/diff/evidence binding and `subdelegation=none` | PASS | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json` | High-risk validation passes; launch remains controller-owned. |

## Requirement Reconciliation
| item | value |
|---|---|
| alignment_status | aligned |
| goal | Candidate removes recursive overlapping work for the approved flat chain and preserves bytes. |
| non-goals | No style, cache, non-subscript, upstream, reviewer-launch, or push scope was added. |
| negative constraints | Generated/corpus/boundary identity is proven; one authorized reviewer slot with no subdelegation was used; workflow files remain local. |
| remaining acceptance | exact-SHA reviewer result and strict closeout |
| evidence | Final Evidence Ledger R1-R6 and linked raw artifacts. |

## Local Enhanced Review
| review target | falsification probe | evidence / outcome | disposition |
|---|---|---|---|
| output drift | Compare complete generated bytes at n=40/80/160/300 and every pre-existing fixture-loader key against the immutable baseline. | All four byte comparisons are true; no baseline fixture key changed or disappeared. | pass |
| guard leakage | Inspect predicates and differentially format accepted/rejected shapes over contexts and line lengths. | Fast path requires direct assignment RHS, monotonic ASCII NAME/NUMBER trailers, and excludes exact optional-parenthesis equality; 3,920-case scan has zero drift. | pass |
| misleading benchmark | Audit interpreter, exact generator, API, warm-up, sample count, medians, and raw artifacts rather than relying on one timing. | CPython 3.12.3; exact required source/API; one warm-up and three recorded samples per n; n160 speedup 60.71x and exponent 0.812. | pass |
| residual non-linearity | Compare deterministic real `_first_right_hand_split` calls and n160→n300 timing growth. | Calls are 90 at n80, n160, and n300; candidate time ratio is 1.666 for a size ratio of 1.875. | pass |
| weak regression oracle | Check that tests observe real formatter work and compare complete output with forced legacy without timing thresholds. | Explicit n80/n160 call ceilings, a static fixture, accepted/rejected guard assertions, and default-88 optional-parenthesis differential all pass. | pass |
| partial-yield/fallback safety | Challenge whether a late batch failure could emit an incomplete transformation. | Review found a hardening opportunity; the helper now accumulates all result lines before yielding. Exact candidate comparison and full suite were rerun afterward. | fixed |

Local verdict: no unresolved S0/S1 finding. Residual risk is the intentionally narrow
syntactic equivalence guard; the exact-SHA read-only reviewer is running.

## Review / Audit Boundary
| item | value |
|---|---|
| Mode | implementation-authorized |
| Write authorization | task |
| Authorization source | user task instruction and explicit “Approved. Proceed with exactly that guarded design.” |
| Allowed write scope | four product files plus required root task state and `.agent-state/runs/t3-5270/` evidence artifacts in the current checkout |
| Prohibited actions | push, upstream PR or comment, prohibited PR/artifact inspection, external write, reviewer launch, and workflow-file commit |
| Finding disposition policy | implementation-approved |
| Transition decision | implement-authorized |

## Isolated Reviewer
> This is the required G16 Role Reviewer assessment. The user explicitly requires a packet but reserves reviewer launch for the controller.

| item | value |
|---|---|
| Required assessment | yes |
| Trigger decision | preferred |
| Reason | user-request |
| Authorization scope | task |
| Authorization source | user message; packet required, local launch prohibited |
| Start required | no |
| Runtime policy status | explicit-delegation-required |
| Start result | explicit-delegation-required |
| Reviewer tool | Codex subagent |
| Model policy | inherit-main-model |
| Reasoning effort | xhigh |
| Timeout policy | review-incomplete |
| Runtime-enforced budget | prompt-soft-limit |
| Input package | `.agent-state/runs/t3-5270/role-review/qa/` |
| Packet validator status | pass |
| Packet validator command | `.agents/scripts/validate-role-review-packet.py --root . --packet .agent-state/runs/t3-5270/role-review/qa --risk-tier high --format json` |
| Packet validator exit code | 0 |
| Packet validator artifact | `.agent-state/runs/t3-5270/role-review/qa/packet-validator.json` |
| Packet retention | retained-during-active-task |
| Durable review summary | `findings.md` F24-F26 and this Role Review Summary |
| Review focus | mixed |
| Secret handling | metadata-only |
| Verdict | blocking |
| Disposition | accepted; product experiment reverted |
| Fallback | local S0/S1 red-team |

## Reviewer Start Authority
| item | value |
|---|---|
| Authority mode | task-authorized |
| Authority source | user message, limited to controller-owned read-only review |
| Scope | read-only reviewer |
| Active task id | `t3-5270` |
| Run ID | `t3-5270` |
| Repo path | `/home/lsy/trials/black-run-1/worktrees/t3-5270` |
| Authorized roles | qa |
| Max reviewers | 1 |
| External model allowed | no |
| Expires | active task completion / target path change / permission expansion / cross-session recovery / external-write |
| Runtime policy status | explicit-delegation-required |
| Runtime-enforced budget | prompt-soft-limit |

## Role Review Summary
| role | trigger | packet | focus | verdict | disposition | unresolved risk |
|---|---|---|---|---|---|---|
| qa | user-request | `.agent-state/runs/t3-5270/role-review/qa/` | mixed | blocking | QA-T3-5270-008/009/010 accepted; stop and revert | Direct batching changes output across base spelling and non-ASCII surrounding contexts; no product candidate deliverable |

## Workflow Trace
| step | status | evidence | notes |
|---|---|---|---|
| risk_tier | done | `task_plan.md#Workflow-Routing` | high / file-linked / complex-task path |
| read_before_decide | done | context-select report; G09/G10/G16/G19/G20/G21 cards; matching references and templates | No structural index and no prohibited external artifact read. |
| requirements-to-plan | done | approved design and root `task_plan.md` | User approved the exact guarded batch design. |
| tooling-map | not-needed | project conventions give direct Python/pytest commands | No alternate tool routing needed. |
| tooling-router | not-needed | targeted source and test entry points are known | Direct execution is safer and narrower. |
| verification_matrix | done | `task_plan.md#Verification-Matrix` | All binding acceptance items are blocking. |
| test_strategy | done | R1 RED/GREEN plus exact output/corpus/full-suite evidence | Timing is independent evidence, not the committed regression oracle. |
| Graphify | not-needed | project policy is disabled and no explicit request exists | Targeted source trace was sufficient. |
| ship-check | partial-only | accepted blocking result and empty final product diff | Product fix prohibited; partial investigation report allowed. |
| implementation | reverted | `1ac5227` | Five experimental product commits preserved in history and explicitly reverted. |
| validation | done | final suite plus product diff | Final safe tree equals base; 481/3 green; candidate compatibility remains blocked. |
| code_review | blocking-as-designed | accepted exact-SHA findings | The reviewer changed the delivery outcome; no approval claim remains. |
| isolated_reviewer | done-blocking | validated exact-SHA packet and strict result | QA-T3-5270-008/009/010 accepted; no second reviewer or subdelegation. |
| red_team | done | Local Enhanced Review falsification table | Drift, guard leakage, evidence validity, residual growth, test strength, and staged scope probed. |
| sensitive_guard | not-needed | no sensitive operation authorized | No secrets, DB, deployment, or external write. |
| push_gate | done | user authorization for review remote; upstream writes remain forbidden | Push only `trial/t3-5270` to `sendream/workflow-validation`. |
| task_closeout | partial | report, empty product diff, final suite, and strict blocking result | Hard product contract unresolved; closeout is explicitly partial rather than PASS. |

## Defect Status
| defect_id | status | owner | verification evidence | allowed to deliver |
|---|---|---|---|---|
| `black-5270` | unresolved-after-trial | main Codex | strict blocking result for `1ff3445`, 133/239 final differential mismatches, and empty net product diff after `1ac5227` | partial report only; no product fix |

## Handoff
- Current phase: partial report delivered on `review/trial/t3-5270` at `fb0e0fe`
- Completed: diagnosis, immutable baseline, deterministic RED, five candidate iterations, four exact-SHA blocking review cycles using one reviewer slot, expanded controller probes, post-lock upstream comparison, explicit product reversion, and final 481/3 suite
- Remaining: fable5 review only; no further product work is authorized in this trial
- Risks: future fixes must optimize the existing splitter without reconstructing layout semantics; corpus/full-suite GREEN alone did not cover assignment, annotation, display-width, and custom-line-length interactions
