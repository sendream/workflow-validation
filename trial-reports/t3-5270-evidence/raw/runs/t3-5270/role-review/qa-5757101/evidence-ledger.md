# Reviewer Evidence Ledger

## Locked Candidate
| item | value |
|---|---|
| task | Black issue #5270 flat consecutive-subscript performance |
| risk / impact | high / file-linked |
| base | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| rejected candidate | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6`; isolated review found accepted blocking byte drift |
| replacement candidate | `575710131f264468b280e5c424f00651da7146c0` |
| diff | `diff.patch`, SHA-256 `9779d088ec6bec8a4ad5a05f463c6f13e90fee12e2a52075dd80ad6b4f72973c` |
| delegation | one qa reviewer slot; same reviewer/tool replaces its result for the new SHA; `subdelegation=none` |

## Product File Bindings
| path | SHA-256 | byte count |
|---|---|---:|
| `CHANGES.md` | `eed71dada3373fcf5f06951ec79b639e2385fb0b55678d26f6124869f2c44730` | 95413 |
| `src/black/linegen.py` | `f577d60d6d536f813e325e2d471b8ab5ca50b20c8eec69b918958042b02dacd0` | 98475 |
| `tests/data/cases/long_flat_subscript_chain.py` | `19a7bb99a0543cc23a38aef6d76f85af88a83fbf9aaa2311bc19f60e59de6e6b` | 859 |
| `tests/test_format.py` | `f2855e403f2aed139d0298369b72c4caa9da7f6205b6c204c90e993413deac8d` | 4810 |

## Acceptance and Scenario Snapshot
| acceptance_id | scenario_id | case_class | required observable | submitted evidence | status |
|---|---|---|---|---|---|
| R1 | S1 | property | Regression is RED before and GREEN after; real split work is bounded linearly. | C2 and C4 prove RED; committed test caps n80 at 160 and n160 at 320 real calls; final observed calls are 90/90/90 at n80/n160/n300. | PASS |
| R2 | S1 | property | Exact CPython 3.12 timing protocol; n160 at least 10x; n300 no quadratic growth. | C5; n160 is 66.34x faster and candidate n160-to-n300 exponent is 0.854. | PASS |
| R3 | S2 | compatibility | Four exact generated outputs and optimized accepted shapes remain byte-identical. | C5 proves four required outputs; C6 compares 162 optimized/forced-legacy cases with 0 mismatches. | PASS |
| R4 | S3 | compatibility | Every pre-existing fixture-loader invocation remains identical and the full suite passes. | C5 preserves all 972 baseline entries including four duplicate keys; C7 reports 486 passed, 3 skipped. | PASS |
| R5 | S4 | boundary | Rejected and accepted neighboring shapes retain legacy formatting. | C5 boundary hashes and C6's 162-case matrix; 89 cases exercised the batch path, 0 mismatches. | PASS |
| R6 | S5 | contract | Minimal product-only commit chain with clean final diff. | `changed-files.txt`, `dirty-worktree-summary.json`, C8, C9, and the locked revision. | PASS |
| R7 | S6 | negative | Valid packet/result; every accepted finding is dispositioned and no blocking finding remains. | Prior result retained under `qa-d522def`; replacement result required after this packet. | UNDER-REVIEW |

## Performance Samples
| n | baseline samples seconds | baseline median | replacement samples seconds | replacement median | speedup | byte identity |
|---:|---|---:|---|---:|---:|---|
| 40 | 0.015312044, 0.014355580, 0.014369468 | 0.014369468 | 0.015068427, 0.014118703, 0.018204006 | 0.015068427 | 0.95x | true |
| 80 | 0.398340223, 0.401371927, 0.400607204 | 0.400607204 | 0.025463322, 0.025003182, 0.024128028 | 0.025003182 | 16.02x | true |
| 160 | 2.345896864, 2.370730568, 2.431998540 | 2.370730568 | 0.036076847, 0.034751732, 0.035733390 | 0.035733390 | 66.34x | true |
| 300 | 8.919318909, 8.811188405, 8.581429225 | 8.811188405 | 0.053094270, 0.065780300, 0.061139664 | 0.061139664 | 144.12x | true |

Raw values and environment metadata are authoritative in C1 and C5. The exact source generator is `"x = a" + "".join(f"[{i}]" for i in range(n)) + "\n"`; the API is `black.format_str(source, mode=black.Mode())`; the clock is `time.perf_counter`; each n has one immediate warm-up and three measured samples; no Black cache participates.

## Reviewer Finding Closure Map
| finding_id | disposition | fix | verification |
|---|---|---|---|
| `QA-T3-5270-001` | accepted | Keep the 2x-width crossing trailer on the recursive head (`batch_start=index+1`) and reject decreasing trailer widths; commit `5757101`. | C4 captures the annotated RED on `d522def`; committed differential tests, C5 corpus identity, and C6 162-case comparison are GREEN. |
| `QA-T3-5270-002` | accepted | Replace the permissive 4x doubling assertion with explicit linear bounds at n80 and n160. | C2 proves the original base regression; final focused/full tests in C7 pass. |
| `QA-T3-5270-003` | accepted | Compare fixture invocations as duplicate-preserving per-key multisets, not a collapsing dictionary. | C5 reports 972 raw baseline entries, 968 unique keys, four retained duplicates, and zero unmatched baseline entries. |

## Review Evidence Index
| check_id | command | exit_code | status | artifact_path | stdout_stderr_summary_path | run_id | timestamp | waiver_id |
|---|---|---:|---|---|---|---|---|---|
| C1 | `/home/lsy/trials/black-run-1/venv/bin/python .agent-state/runs/t3-5270/scripts/evidence_capture.py --phase baseline` | 0 | PASS | `.agent-state/runs/t3-5270/manifest.json` | `.agent-state/runs/t3-5270/outputs/stdout.txt` | `t3-5270` | `2026-08-23T07:34:20Z` | not-needed |
| C2 | `env -u NO_COLOR ... pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 1 | EXPECTED-RED | `.agent-state/runs/t3-5270/red/t3-5270-red/manifest.json` | `.agent-state/runs/t3-5270/red/t3-5270-red/outputs/stdout.txt` | `t3-5270-red` | `2026-08-23T07:36:07Z` | not-needed |
| C3 | isolated qa review of `d522def` | 0 | BLOCKING | `.agent-state/runs/t3-5270/role-review/qa-d522def/role-review-result.json` | same JSON artifact | `qa-d522def` | `2026-08-23` | not-needed |
| C4 | focused reviewer counterexample and strengthened work tests on `d522def` | 1 | EXPECTED-RED | `.agent-state/runs/t3-5270-reviewer-red/manifest.json` | `.agent-state/runs/t3-5270-reviewer-red/outputs/stdout.txt` | `t3-5270-reviewer-red` | `2026-08-23T08:17:52Z` | not-needed |
| C5 | final exact benchmark/output/duplicate-safe corpus/boundary capture | 0 | PASS | `.agent-state/runs/t3-5270-candidate-final-v2/manifest.json` | `.agent-state/runs/t3-5270-candidate-final-v2/outputs/stdout.txt` | `t3-5270-candidate-final-v2` | `2026-08-23T08:36:48Z` | not-needed |
| C6 | final 162-case optimized-versus-legacy differential | 0 | PASS | `.agent-state/runs/t3-5270-legacy-differential-v2/manifest.json` | `.agent-state/runs/t3-5270-legacy-differential-v2/outputs/stdout.txt` | `t3-5270-legacy-differential-v2` | `2026-08-23T08:35:37Z` | not-needed |
| C7 | `env -u NO_COLOR ... python -m pytest -n auto` | 0 | PASS | `.agent-state/runs/t3-5270-full-suite-final-v2/manifest.json` | `.agent-state/runs/t3-5270-full-suite-final-v2/outputs/stdout.txt` | `t3-5270-full-suite-final-v2` | `2026-08-23T08:34:29Z` | not-needed |
| C8 | `python -m black --check src/black/linegen.py tests/test_format.py` | 0 | PASS | `.agent-state/runs/t3-5270-black-check-v2/manifest.json` | `.agent-state/runs/t3-5270-black-check-v2/outputs/stdout.txt` | `t3-5270-black-check-v2` | `2026-08-23T08:34:48Z` | not-needed |
| C9 | `git diff 868d4ef..HEAD --check` | 0 | PASS | `.agent-state/runs/t3-5270-diff-check-v2/manifest.json` | `.agent-state/runs/t3-5270-diff-check-v2/outputs/stdout.txt` | `t3-5270-diff-check-v2` | `2026-08-23T08:34:33Z` | not-needed |
