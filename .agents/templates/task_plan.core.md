# Task Plan

> Core template for the current active task. Copy this file to project-root `task_plan.md`; appendices under `.agents/templates/appendices/` are snippets only and must be copied back into root `task_plan.md` when triggered.

## Task
一句话说明这次任务要解决什么问题。

## Current phase
- 阶段：理解中 / 规划中 / 执行中 / 验证中 / 收口中 / 已完成
- Active task id：optional / 待填写

## Workflow Routing
| item | value |
|---|---|
| Risk Tier | low / standard / high / release |
| Impact Scope | visible / file-linked / cross-package / external-system |
| Task path | fast path / complex-task path |
| Reason | 待填写 |

## Requirement Contract
| id | requirement | acceptance | evidence |
|---|---|---|---|
| R1 | 待填写 | 待填写 | 待填写 |

## Scope
- In scope:
- Out of scope:

## Negative Constraints
- 待填写

## Verification Matrix
| acceptance / risk | scenario_id | case_class | evidence method | required checks | test oracle / independence | blocking | evidence |
|---|---|---|---|---|---|---|---|
| 待填写 | not-needed / S1 | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | command / artifact / manual QA / not-needed | 待填写 | requirement / existing behavior / fixture / human domain / not-needed | block / warn / not-needed | 待填写 |

## Execution Table
| slice_id | slice_type | files | action | acceptance | verify | done |
|---|---|---|---|---|---|---|
| E1 | story / risk / technical | 待填写 | 待填写 | 待填写 | 待填写 | pending |

## Appendix Triggers
Copy matching snippets from `.agents/templates/appendices/` back into this root file when triggered:

| trigger | appendix |
|---|---|
| behavior / example contract, field contract, unclear negative or boundary behavior | `task_plan.behavior-appendix.md` |
| high/release, external-system, release artifact, role reviewer, structural-index query | `task_plan.risk-release-appendix.md` |
| defect / regression / production issue | `task_plan.defect-appendix.md` |

## Risks
- 待填写
