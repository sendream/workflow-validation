# Reviewer Evidence Ledger

## Locked Candidate
| item | value |
|---|---|
| task | Black issue #5270 flat consecutive-subscript performance |
| risk / impact | high / file-linked |
| base | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| rejected candidate | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6`; isolated review found accepted blocking byte drift |
| replacement candidate | `1ff34455be35812ab10cebd66e6730f68eab1196` |
| diff | `diff.patch`, SHA-256 `3b6650e7561f3ac48c37a14dabb35b9c6654ee7937974c0aa453bdbfb0aff20f` |
| delegation | one qa reviewer slot; same reviewer/tool replaces its result for the new SHA; `subdelegation=none` |

## Product File Bindings
| path | SHA-256 | byte count |
|---|---|---:|
| `CHANGES.md` | `eed71dada3373fcf5f06951ec79b639e2385fb0b55678d26f6124869f2c44730` | 95413 |
| `src/black/linegen.py` | `bb4fd18691b1992114b4569ae0e5b4048f46ca00c48ce41c7af08ff7a82ddfe5` | 98639 |
| `tests/data/cases/long_flat_subscript_chain.py` | `19a7bb99a0543cc23a38aef6d76f85af88a83fbf9aaa2311bc19f60e59de6e6b` | 859 |
| `tests/test_format.py` | `62f86d86d3df7e0be8c1995bb55374a8cb24dff5d2c8c7a4261d70884a60f835` | 5926 |

## Acceptance and Scenario Snapshot
| acceptance_id | scenario_id | case_class | required observable | submitted evidence | status |
|---|---|---|---|---|---|
| R1 | S1 | property | Regression is RED before and GREEN after; real split work is bounded linearly. | C2 and C4 prove RED; committed test caps n80 at 160 and n160 at 320 real calls; final observed calls are 90/90/90 at n80/n160/n300. | PASS |
| R2 | S1 | property | Exact CPython 3.12 timing protocol; n160 at least 10x; n300 no quadratic growth. | C10; n160 is 60.71x faster and candidate n160-to-n300 exponent is 0.812. | PASS |
| R3 | S2 | compatibility | Four exact generated outputs and optimized accepted shapes remain byte-identical. | C10 proves four required outputs; C11 exhausts line lengths 1..140 across 28 context/body families with 0 mismatches after the exact-prefix fallback. | PASS |
| R4 | S3 | compatibility | Every pre-existing fixture-loader invocation remains identical and the full suite passes. | C10 preserves all 972 baseline entries including four duplicate keys; C12 reports 490 passed, 3 skipped. | PASS |
| R5 | S4 | boundary | Rejected and accepted neighboring shapes retain legacy formatting. | C11 covers 3,920 line-length/context cases with 1,216 accepted fast-path cases and zero mismatch; C13 binds every prior counterexample. | PASS |
| R6 | S5 | contract | Minimal product-only commit chain with clean final diff. | `changed-files.txt`, `dirty-worktree-summary.json`, C8, C9, and the locked revision. | PASS |
| R7 | S6 | negative | Valid packet/result; every accepted finding is dispositioned and no blocking finding remains. | Prior results retained under `qa-d522def`, `qa-5757101`, and `qa-483b25d`; a fresh exact-SHA result is required after this packet. | UNDER-REVIEW |

## Performance Samples
| n | baseline samples seconds | baseline median | replacement samples seconds | replacement median | speedup | byte identity |
|---:|---|---:|---|---:|---:|---|
| 40 | 0.015312044, 0.014355580, 0.014369468 | 0.014369468 | 0.016438062, 0.022077992, 0.016677293 | 0.016677293 | 0.86x | true |
| 80 | 0.398340223, 0.401371927, 0.400607204 | 0.400607204 | 0.027540927, 0.026783178, 0.028883082 | 0.027540927 | 14.55x | true |
| 160 | 2.345896864, 2.370730568, 2.431998540 | 2.370730568 | 0.038448735, 0.040411329, 0.039052603 | 0.039052603 | 60.71x | true |
| 300 | 8.919318909, 8.811188405, 8.581429225 | 8.811188405 | 0.061368516, 0.082835787, 0.065071453 | 0.065071453 | 135.40x | true |

Raw values and environment metadata are authoritative in C1 and C5. The exact source generator is `"x = a" + "".join(f"[{i}]" for i in range(n)) + "\n"`; the API is `black.format_str(source, mode=black.Mode())`; the clock is `time.perf_counter`; each n has one immediate warm-up and three measured samples; no Black cache participates.

## Reviewer Finding Closure Map
| finding_id | disposition | fix | verification |
|---|---|---|---|
| `QA-T3-5270-001` | accepted | Keep the 2x-width crossing trailer on the recursive head (`batch_start=index+1`) and reject decreasing trailer widths; commit `5757101`. | C4 captures the annotated RED on `d522def`; committed differential tests and C10 corpus identity are GREEN. |
| `QA-T3-5270-002` | accepted | Replace the permissive 4x doubling assertion with explicit linear bounds at n80 and n160. | C2 proves the original base regression; final focused/full tests in C7 pass. |
| `QA-T3-5270-003` | accepted | Compare fixture invocations as duplicate-preserving per-key multisets, not a collapsing dictionary. | C5 reports 972 raw baseline entries, 968 unique keys, four retained duplicates, and zero unmatched baseline entries. |
| `QA-T3-5270-004` | accepted | Remove all STRING trailers from the fast-path grammar; they use the unchanged legacy splitter. | C13 captures the CJK STRING RED then GREEN; C11 includes increasing-width CJK STRING shapes and reports zero mismatches. |
| `QA-T3-5270-005` | accepted | Add accepted increasing-width NUMBER and rejected increasing-width CJK STRING cases, and assert whether the batch path accepted each case. | C13 reports the focused guard cases pass; C11 independently varies 290 contexts and widths. |
| controller-wide-NAME probe | accepted | Require every accepted NAME/NUMBER body spelling to be ASCII; wide identifiers use the legacy path. | C13 captures the wide-NAME RED/GREEN; C11 includes increasing CJK NAME chains and reports zero mismatches. |
| `QA-T3-5270-006` | accepted | Fail open when the cumulative display width through the RHS base exactly equals `mode.line_length`, preserving legacy optional RHS parentheses. | C13 captures a default-88 long-LHS RED/GREEN; C11 exhausts line lengths 1..140 and reports zero mismatch. |
| `QA-T3-5270-007` | accepted | Parameterize the focused default-88 exact-prefix boundary and add an exhaustive line-length/context evidence scan. | C11 covers equal/increasing NAME/NUMBER bodies under seven assignment contexts at every line length 1..140. |

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
| C10 | final benchmark/output/duplicate-safe corpus capture after optional-paren guard | 0 | PASS | `.agent-state/runs/t3-5270-candidate-final-v5/manifest.json` | `.agent-state/runs/t3-5270-candidate-final-v5/outputs/stdout.txt` | `t3-5270-candidate-final-v5` | `2026-08-23` | not-needed |
| C11 | exhaustive line-length/context optimized-versus-legacy scan | 0 | PASS | `.agent-state/runs/t3-5270-line-length-scan-green/manifest.json` | `.agent-state/runs/t3-5270-line-length-scan-green/outputs/stdout.txt` | `t3-5270-line-length-scan-green` | `2026-08-23` | not-needed |
| C12 | `env -u NO_COLOR ... python -m pytest -n auto` | 0 | PASS | `.agent-state/runs/t3-5270-full-suite-final-v5/manifest.json` | `.agent-state/runs/t3-5270-full-suite-final-v5/outputs/stdout.txt` | `t3-5270-full-suite-final-v5` | `2026-08-23` | not-needed |
| C13 | annotated/CJK STRING/CJK NAME/optional-paren RED-GREEN probes | 1/0 | RED/GREEN | reviewer RED/GREEN manifests plus `.agent-state/runs/t3-5270-optional-paren-red/manifest.json` and `t3-5270-optional-paren-green/manifest.json` | paired stdout artifacts | focused run IDs | `2026-08-23` | not-needed |
| C14 | final Black check and base-to-candidate diff check | 0 | PASS | `.agent-state/runs/t3-5270-black-check-v5/manifest.json`; `.agent-state/runs/t3-5270-diff-check-v5/manifest.json` | paired stdout artifacts | `t3-5270-black-check-v5`; `t3-5270-diff-check-v5` | `2026-08-23` | not-needed |
