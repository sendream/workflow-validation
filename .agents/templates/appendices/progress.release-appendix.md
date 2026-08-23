# Progress Appendix: Release Artifact Source Gate

> Snippet only. Copy relevant sections into root `progress.md` when release/external-system artifact handling is triggered. This file is not task state.

## Release Artifact Source Gate
| item | value |
|---|---|
| Required | yes / no |
| Source mode | clean-source-build / source-manifest-build / allowed-diff-build / blocked / not-needed |
| Release-source packet | `.agent-state/runs/<run_id>/release-source/` / not-needed |
| Artifact sha256 | 待填写 / not-needed |
| Clean source evidence | git status / source tree evidence path / not-needed |
| Git status evidence | `.agent-state/runs/<run_id>/release-source/git-status.txt` / not-needed |
| Intended source files | `.agent-state/runs/<run_id>/release-source/intended-source-files.json` / not-needed |
| Source manifest | `.agent-state/runs/<run_id>/release-source/source-manifest.json` / not-needed |
| Legacy allowed source scope | compatibility-only: `.agent-state/runs/<run_id>/release-source/allowed-source-scope.txt` / not-needed |
| Unrelated dirty source disposition | excluded / reviewed / blocked / not-needed |
| Explicit user risk acceptance | none / required / accepted |
| Attestation mode | local-only / GitHub artifact attestation / SLSA / SBOM / not-needed |

## Release S0/S1 Red-team
| check | status | evidence / notes |
|---|---|---|
| permissions/auth | pass / fail / not-needed | 待填写 |
| production config | pass / fail / not-needed | 待填写 |
| data/runtime contamination | pass / fail / not-needed | 待填写 |
| rollback point | pass / fail / not-needed | 待填写 |
