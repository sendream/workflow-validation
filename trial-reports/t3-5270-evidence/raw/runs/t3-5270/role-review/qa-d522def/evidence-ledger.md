# Reviewer Evidence Ledger

## Locked Candidate
| item | value |
|---|---|
| task | Black issue #5270 flat consecutive-subscript performance |
| risk / impact | high / file-linked |
| base | `868d4efdbcaf4c29387a99ba854be406b1a1ec99` |
| candidate | `d522defdf8a6ea6858aa0b95b34b31a3865a55c6` |
| diff | `diff.patch`, SHA-256 `c0408bf6ec079c040a5ce266f243a07fee0aaf213c93428177f37d3dbb6a5b51` |
| delegation | none; controller owns reviewer launch |

## Product File Bindings
| path | SHA-256 | byte count |
|---|---|---:|
| `CHANGES.md` | `eed71dada3373fcf5f06951ec79b639e2385fb0b55678d26f6124869f2c44730` | 95413 |
| `src/black/linegen.py` | `86ea0ebd231e2c6256312fea746934c0cc4befc6f01d204004dec857aecfb684` | 97944 |
| `tests/data/cases/long_flat_subscript_chain.py` | `19a7bb99a0543cc23a38aef6d76f85af88a83fbf9aaa2311bc19f60e59de6e6b` | 859 |
| `tests/test_format.py` | `bc78ccf847722419b164bf97b103652fdaedf8aef41cd14316389c3eb63233ee` | 3816 |

## Acceptance and Scenario Snapshot
| acceptance_id | scenario_id | case_class | required observable | submitted evidence | status |
|---|---|---|---|---|---|
| R1 | S1 | property | Deterministic regression is RED before and GREEN after; real split work no longer grows quadratically. | C2 and C3; RED 1,700 calls at n80 versus 68 at n40, GREEN within the coarse bound. | PASS |
| R2 | S1 | property | Exact CPython 3.12 timing protocol; n160 at least 10x; n300 no quadratic growth. | C1 and C4; n160 84.13598x, candidate n160-to-n300 exponent 0.77859. | PASS |
| R3 | S2 | compatibility | Four exact generated outputs remain byte-identical. | C4; all four full-byte comparisons true with unchanged SHA-256 and byte counts. | PASS |
| R4 | S3 | compatibility | Every pre-existing fixture-loader output remains identical and the full suite passes. | C4 and C5; no changed or removed baseline key; 483 passed, 3 skipped. | PASS |
| R5 | S4 | boundary | Non-subscript and mixed trailer chains retain legacy formatting. | C4; explicit attribute/call and mixed subscript/call hashes are identical; corpus comparison is clean. | PASS |
| R6 | S5 | contract | One product-only commit with clean diff. | `changed-files.txt`, `dirty-worktree-summary.json`, C6, and the locked revision. | PASS |
| R7 | S6 | negative | Validated reviewer packet; no local reviewer launch or subdelegation. | This packet; validator artifact will be added after validation. | UNDER-VALIDATION |

## Performance Samples
| n | baseline samples seconds | baseline median | candidate samples seconds | candidate median | byte identity |
|---:|---|---:|---|---:|---|
| 40 | 0.015312044, 0.014355580, 0.014369468 | 0.014369468 | 0.014760263, 0.014542166, 0.015388390 | 0.014760263 | true |
| 80 | 0.398340223, 0.401371927, 0.400607204 | 0.400607204 | 0.017265980, 0.016299575, 0.018255734 | 0.017265980 | true |
| 160 | 2.345896864, 2.370730568, 2.431998540 | 2.370730568 | 0.026865375, 0.028177370, 0.028382554 | 0.028177370 | true |
| 300 | 8.919318909, 8.811188405, 8.581429225 | 8.811188405 | 0.044809322, 0.045968159, 0.055835109 | 0.045968159 | true |

Raw values and environment metadata are authoritative in C1 and C4. The exact source generator is `"x = a" + "".join(f"[{i}]" for i in range(n)) + "\n"`; the API is `black.format_str(source, mode=black.Mode())`; the clock is `time.perf_counter`; each n has one warm-up and three measured samples; no Black cache participates.

## Review Evidence Index
| check_id | command | exit_code | status | artifact_path | stdout_stderr_summary_path | run_id | timestamp | waiver_id |
|---|---|---:|---|---|---|---|---|---|
| C1 | `/home/lsy/trials/black-run-1/venv/bin/python .agent-state/runs/t3-5270/scripts/evidence_capture.py --phase baseline` | 0 | PASS | `.agent-state/runs/t3-5270/manifest.json` | `.agent-state/runs/t3-5270/outputs/stdout.txt` | `t3-5270` | `2026-08-23T07:34:20Z` | not-needed |
| C2 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 1 | FAILED | `.agent-state/runs/t3-5270/red/t3-5270-red/manifest.json` | `.agent-state/runs/t3-5270/red/t3-5270-red/outputs/stdout.txt` | `t3-5270-red` | `2026-08-23T07:36:07Z` | not-needed |
| C3 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest tests/test_format.py::test_long_flat_subscript_chain_split_work_is_linear -q` | 0 | PASS | `.agent-state/runs/t3-5270/green/t3-5270-green/manifest.json` | `.agent-state/runs/t3-5270/green/t3-5270-green/outputs/stdout.txt` | `t3-5270-green` | `2026-08-23T07:40:21Z` | not-needed |
| C4 | `/home/lsy/trials/black-run-1/venv/bin/python .agent-state/runs/t3-5270/scripts/evidence_capture.py --phase candidate` | 0 | PASS | `.agent-state/runs/t3-5270/candidate/t3-5270-candidate-final/manifest.json` | `.agent-state/runs/t3-5270/candidate/t3-5270-candidate-final/outputs/stdout.txt` | `t3-5270-candidate-final` | `2026-08-23T07:45:13Z` | not-needed |
| C5 | `env -u NO_COLOR /home/lsy/trials/black-run-1/venv/bin/python -m pytest -n auto` | 0 | PASS | `.agent-state/runs/t3-5270/final/t3-5270-full-suite-final/manifest.json` | `.agent-state/runs/t3-5270/final/t3-5270-full-suite-final/outputs/stdout.txt` | `t3-5270-full-suite-final` | `2026-08-23T07:45:36Z` | not-needed |
| C6 | `git diff --check` | 0 | PASS | `.agent-state/runs/t3-5270/final/t3-5270-diff-check/manifest.json` | `.agent-state/runs/t3-5270/final/t3-5270-diff-check/outputs/stdout.txt` | `t3-5270-diff-check` | `2026-08-23T07:45:48Z` | not-needed |
