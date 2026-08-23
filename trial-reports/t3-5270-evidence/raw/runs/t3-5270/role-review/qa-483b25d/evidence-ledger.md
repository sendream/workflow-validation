# Reviewer Evidence Ledger

## Locked Candidate
| item | value |
|---|---|
| task | Black issue #5270 flat consecutive-subscript performance |
| risk / impact | high / file-linked |
| base | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| rejected candidate | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6`; isolated review found accepted blocking byte drift |
| replacement candidate | `483b25d3c73ad38148343f4417e21262425162d5` |
| diff | `diff.patch`, SHA-256 `f7e69f7e330936cc22ff0079ba22fcab7df1dff3a4a7daa3a5e966c3f70046ea` |
| delegation | one qa reviewer slot; same reviewer/tool replaces its result for the new SHA; `subdelegation=none` |

## Product File Bindings
| path | SHA-256 | byte count |
|---|---|---:|
| `CHANGES.md` | `eed71dada3373fcf5f06951ec79b639e2385fb0b55678d26f6124869f2c44730` | 95413 |
| `src/black/linegen.py` | `fa6b1692ed1ba4acb9ff556e6144cf96a44b1b9d539b0b849e3c5ff5ac3335c1` | 98501 |
| `tests/data/cases/long_flat_subscript_chain.py` | `19a7bb99a0543cc23a38aef6d76f85af88a83fbf9aaa2311bc19f60e59de6e6b` | 859 |
| `tests/test_format.py` | `37ac7e6241a5fb11d7c96eab3b53a32f83cb8c5242879aba046780d714c1908d` | 5882 |

## Acceptance and Scenario Snapshot
| acceptance_id | scenario_id | case_class | required observable | submitted evidence | status |
|---|---|---|---|---|---|
| R1 | S1 | property | Regression is RED before and GREEN after; real split work is bounded linearly. | C2 and C4 prove RED; committed test caps n80 at 160 and n160 at 320 real calls; final observed calls are 90/90/90 at n80/n160/n300. | PASS |
| R2 | S1 | property | Exact CPython 3.12 timing protocol; n160 at least 10x; n300 no quadratic growth. | C10; n160 is 57.25x faster and candidate n160-to-n300 exponent is 0.593. | PASS |
| R3 | S2 | compatibility | Four exact generated outputs and optimized accepted shapes remain byte-identical. | C10 proves four required outputs; C11 compares 290 optimized/forced-legacy cases with 0 mismatches after STRING and wide NAME trailers were excluded. | PASS |
| R4 | S3 | compatibility | Every pre-existing fixture-loader invocation remains identical and the full suite passes. | C10 preserves all 972 baseline entries including four duplicate keys; C12 reports 489 passed, 3 skipped. | PASS |
| R5 | S4 | boundary | Rejected and accepted neighboring shapes retain legacy formatting. | C10 boundary hashes, C11's 290-case matrix, and C13 focused guard cases; 86 matrix cases exercised the ASCII NAME/NUMBER batch path, 0 mismatches. | PASS |
| R6 | S5 | contract | Minimal product-only commit chain with clean final diff. | `changed-files.txt`, `dirty-worktree-summary.json`, C8, C9, and the locked revision. | PASS |
| R7 | S6 | negative | Valid packet/result; every accepted finding is dispositioned and no blocking finding remains. | Prior results retained under `qa-d522def` and `qa-5757101`; a fresh exact-SHA result is required after this packet. | UNDER-REVIEW |

## Performance Samples
| n | baseline samples seconds | baseline median | replacement samples seconds | replacement median | speedup | byte identity |
|---:|---|---:|---|---:|---:|---|
| 40 | 0.015312044, 0.014355580, 0.014369468 | 0.014369468 | 0.015122296, 0.015851200, 0.016673040 | 0.015851200 | 0.91x | true |
| 80 | 0.398340223, 0.401371927, 0.400607204 | 0.400607204 | 0.032643981, 0.026268525, 0.028470058 | 0.028470058 | 14.07x | true |
| 160 | 2.345896864, 2.370730568, 2.431998540 | 2.370730568 | 0.041413740, 0.042032702, 0.037926508 | 0.041413740 | 57.25x | true |
| 300 | 8.919318909, 8.811188405, 8.581429225 | 8.811188405 | 0.060106199, 0.069619147, 0.057775732 | 0.060106199 | 146.59x | true |

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
| C10 | final benchmark/output/duplicate-safe corpus capture after ASCII guard narrowing | 0 | PASS | `.agent-state/runs/t3-5270-candidate-final-v4/manifest.json` | `.agent-state/runs/t3-5270-candidate-final-v4/outputs/stdout.txt` | `t3-5270-candidate-final-v4` | `2026-08-23T09:05:50Z` | not-needed |
| C11 | expanded 290-case optimized-versus-legacy differential | 0 | PASS | `.agent-state/runs/t3-5270-legacy-differential-v4/manifest.json` | `.agent-state/runs/t3-5270-legacy-differential-v4/outputs/stdout.txt` | `t3-5270-legacy-differential-v4` | `2026-08-23T09:04:56Z` | not-needed |
| C12 | `env -u NO_COLOR ... python -m pytest -n auto` | 0 | PASS | `.agent-state/runs/t3-5270-full-suite-final-v4/manifest.json` | `.agent-state/runs/t3-5270-full-suite-final-v4/outputs/stdout.txt` | `t3-5270-full-suite-final-v4` | `2026-08-23` | not-needed |
| C13 | CJK STRING and wide-NAME RED/GREEN guard probes | 1/0 | RED/GREEN | `.agent-state/runs/t3-5270-reviewer-red-v2/manifest.json`; `.agent-state/runs/t3-5270-reviewer-green-v2/manifest.json`; `.agent-state/runs/t3-5270-wide-name-red/manifest.json`; `.agent-state/runs/t3-5270-wide-name-green/manifest.json` | paired stdout artifacts | four focused run IDs | `2026-08-23` | not-needed |
| C14 | final Black check and base-to-candidate diff check | 0 | PASS | `.agent-state/runs/t3-5270-black-check-v4/manifest.json`; `.agent-state/runs/t3-5270-diff-check-v4/manifest.json` | paired stdout artifacts | `t3-5270-black-check-v4`; `t3-5270-diff-check-v4` | `2026-08-23` | not-needed |
