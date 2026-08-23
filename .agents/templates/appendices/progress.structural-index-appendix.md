# Progress Appendix: Structural Index Query Evidence

> Snippet only. Copy relevant sections into root `progress.md` when Structural Index / Graphify / CodeGraph is used. This file is not task state.

## Structural Index Query Evidence
| provider | status | decision | query_intent | source_root_id | source_root | root_freshness | query_count | summary_path | source_confirmed | source_confidence | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none / graphify / codegraph / both | disabled / missing / enabled-fresh / enabled-stale / trial | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | impact / callers / callees / affected-tests / symbol-search / not-needed | not-needed / registry:<root_id> | `待填写` / not-needed | fresh / stale / missing / unknown / not-needed | 0 / 1 / 3 / explicit | `.agent-state/runs/<run_id>/structural-index/...` / not-needed | yes / no / not-needed | source-confirmed / test-confirmed / index-candidate / stale-candidate / unknown / not-needed | 待填写 |

## Structural Index Pilot Effect
| provider | decision | source_root | decision_changed | avoided_wrong_edit | tests_or_files_discovered | false_negative_or_empty_signal | elapsed_or_saved_time | artifact_size_or_cost | root_freshness | freshness_basis | roi_signal | roi_claim_status | source_confirmed | reindexRecommended | disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| none / graphify / codegraph / both | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | `待填写` / not-needed | yes / no / unknown / not-needed | yes / no / unknown / not-needed | tests / files / none / unknown / not-needed | affected-tests-empty / callers-empty / callees-empty / false-negative / none / unknown / not-needed | minutes saved / elapsed minutes / unknown / not-needed | low / medium / high / bytes / not-needed | fresh / stale / missing / unknown / not-needed | metadata / query-time / source-snapshot / not-needed | changed-plan / found-files / found-tests / avoided-wrong-edit / saved-time / none / not-needed | not-claimed / candidate / proven-positive / neutral / negative / not-needed | yes / no / not-needed | yes / no / unknown / not-needed | useful / neutral / costly / defer / not-needed |
