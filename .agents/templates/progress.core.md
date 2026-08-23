# Progress

> Core template for the current active task. Copy this file to project-root `progress.md`; appendices under `.agents/templates/appendices/` are snippets only and must be copied back into root `progress.md` when triggered.

## Current Status
- 当前阶段：未开始 / 理解中 / 规划中 / 执行中 / 验证中 / 已完成
- Active task id：`待填写`
- Lifecycle state：planned / in_progress / verifying / ready_to_submit / submitted / archived / blocked / deferred / cancelled
- Template scale：compact / normal / full
- Current focus：待填写
- Next Action：待填写
- Blocked By：none / 待填写

## Changed Files Manifest
| path | type | reason |
|---|---|---|
| 待填写 | source / test / docs / config / generated / workflow | 待填写 |

## Validation
| command | exit_code | result | artifact |
|---|---:|---|---|
| 待填写 | 待填写 | pass / fail / skipped / waived | `.agent-state/runs/<run_id>/manifest.json` / manual QA note only / not-needed |

## Acceptance Evidence
| acceptance_id | scenario_id | evidence | status | notes |
|---|---|---|---|---|
| R1 | not-needed / S1 | command / artifact / manual QA note only / not-needed | PASS / FAIL / WAIVED / NOT-RUN | 待填写 |

## Diff-to-Plan
| check | status | evidence / notes |
|---|---|---|
| changed files match Scope | pending / pass / fail | 待填写 |
| Negative Constraints respected | pending / pass / fail | 待填写 |
| unexpected files explained | pending / pass / fail / not-needed | 待填写 |

## Appendix Triggers
Copy matching snippets from `.agents/templates/appendices/` back into root `progress.md` when triggered:

| trigger | appendix |
|---|---|
| workflow-source change, or explicit path-consistency / trajectory debug | `progress.workflow-trace-appendix.md` |
| high/release evidence, strict closeout, command PASS evidence | `progress.evidence-waiver-appendix.md` |
| release artifact / external-system deploy package | `progress.release-appendix.md` |
| Role Reviewer assessment / policy-auto reviewer | `progress.reviewer-appendix.md` |
| Structural Index / Graphify / CodeGraph used | `progress.structural-index-appendix.md` |
| real project workflow feedback / trajectory candidate | `progress.trace-to-eval-appendix.md` |
| derived report / gate / review requires explicit human decision | `progress.human-decision-appendix.md` |
| workflow-source mechanism, validator, eval, template, or evolution candidate changes | `workflow-source-change-attribution.md` |

## Handoff
- Current phase:
- Completed:
- Remaining:
- Risks:
