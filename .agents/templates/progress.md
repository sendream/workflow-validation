# Progress

> Frozen compatibility full template. Canonical design source is `progress.core.md` plus `.agents/templates/appendices/`. Do not add or change fields here; edit core or the owning appendix.

## Current Status
- 当前阶段：未开始 / 理解中 / 规划中 / 执行中 / 验证中 / 已完成
- 最后更新时间：待填写
- Active task id：`待填写`
- Lifecycle state：planned / in_progress / verifying / ready_to_submit / submitted / archived / blocked / deferred / cancelled
- 当前 owner：待填写
- 当前负责事项：待填写
- Template scale：compact / normal / full
- Current focus：待填写
- Active slice id：not-needed / 待填写
- Rollover state：none / split-needed / handoff-ready / carried-forward / blocked
- Rollover target：not-needed / slice_id / task_id / handoff / 待填写
- Structural Index provider：none / graphify / codegraph / both
- Structural Index Decision：none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query
- Structural Index freshness：fresh / stale / missing / unknown / not-needed
- 三文件状态：active / submitted / archived / cleared / needs-sync / stale
- Task closeout status：not-needed / focused / strict-pass / strict-fail / blocked
- Archive status：not-needed / archive-ready / archived-at `.agents/tasks/<task-id>/` / archive-deferred
- Next Action：待填写
- Blocked By：none / 待填写

> Active task hard rule: complex / high / release 任务继续 coding、deploy 或 ship-check 前，`task_plan.md`、`progress.md`、`findings.md` 的 active task id 必须一致；不一致时先迁移/归档三文件。
> Lifecycle rule: `ready_to_submit` / `submitted` 只描述任务 handoff 状态，不镜像 commit、push 或 upstream 状态；归档完成后转为 `archived` 或把根三文件清回下一 active task。`task_closeout=strict-pass` 不能和 `active / in_progress` 根状态并存。
> Compact rule: compact / normal 任务只需保留当前风险档位触发的章节；未触发的 release、campaign、reviewer 长表可以省略而不是逐段填满 `not-needed`。Compaction line budget 按已填写有效内容计算，不按原始模板占位行计算。
> Next Action rule: high / release handoff 的 `Next Action` 必须是单一、可执行、可验证或带停止条件的下一步；不要写成“继续优化 / 继续推进 / TBD / follow up”这类空泛方向。
> Rollover rule: `Rollover state` 只描述当前 active slice 是否需要切分 / 交接，不创建第二套计划；slice 计划仍以 `task_plan.md#Execution Table` 为准，证据仍以 Run Evidence / Final Evidence Ledger 为准。

## Progress Scale Budget
> 只记录实际触发的 workflow sections。省略未触发章节不是 validator failure；相反，compact/normal 任务复制 full release/reviewer/campaign 长表会增加上下文噪声。

| scale | keep | optional / triggered only | omit by default |
|---|---|---|---|
| compact | Current Status, Summary, Changed Files Manifest, Validation, Handoff | Workflow Trace, Final Evidence Ledger if behavior/evidence risk exists | Role Review, Campaign, Release Artifact Source, Waiver long tables |
| normal | compact + Workflow Trace, Run Evidence, Review Finding Closure when applicable | Structural Index, Trace-to-Eval, Docs Fact Drift | release-only provenance and dynamic campaign sections |
| full | normal + Final Evidence Ledger, Waivers, Role Review, Release / External gates as triggered | Campaign only for 2+ reviewers / explicit experiment / broad audit | none, but keep long raw logs in `.agent-state/runs/` |

## Summary
一句话说明当前进展。

## Delivery Metadata
- Task ID：optional / 待填写
- Run ID：optional / 待填写
- Trace ID：optional / 待填写
- Requirement ID：optional / 待填写
- Feature ID：optional / 待填写
- Issue ID：optional / 待填写
- PR ID：optional / 待填写
- Release note：optional / 待填写

## Workflow Trace
> Workflow Trace 只回答“本任务是否走了该走的 workflow step”。它不是第二状态源，不替代 `Final Evidence Ledger`、`Verification Waivers`、`Release Artifact Source Gate` 或 reviewer finding disposition。
> 如生成 JSON trace，只能作为派生 artifact 放在 `.agent-state/runs/<run_id>/workflow-trace.json`，并引用三文件 / validator artifact；不要在项目根创建 `workflow_trace.json`、`workflow-plan.json` 或 `workflow-run.json`。
> Agent-view debugging 复用本节；evidence / notes 可用 `expected=...; actual=...; failure_class=...; artifact=...`。若是真实 workflow miss，再写 `Trace-to-Eval Intake`；不要在项目根创建 agent-view/debug JSON 或粘贴 raw logs。

| step | status | evidence | notes |
|---|---|---|---|
| grill_check | not-needed / required / done / waived | 待填写 | 待填写 |
| risk_tier | low / standard / high / release | 待填写 | 待填写 |
| impact_scope | visible / file-linked / cross-package / external-system | 待填写 | 待填写 |
| read_before_decide | not-needed / done / missing | 待填写 | 待填写 |
| requirements-to-plan | not-needed / used | 待填写 | 待填写 |
| tooling-map | not-needed / read / missing / unavailable | 待填写 | 待填写 |
| tooling-router | not-needed / planned / run / validate-only | 待填写 | 待填写 |
| verification_matrix | not-needed / drafted / checked | 待填写 | 待填写 |
| test_strategy | not-needed / drafted / checked | 待填写 | 待填写 |
| test_evidence_gate | not-needed / required / done / waived | 待填写 | 待填写 |
| requirement_reconciliation | not-needed / pass / needs-human-check / mismatch / waived | 待填写 | 待填写 |
| defect_management | not-needed / drafted / triaged / verified / waived | 待填写 | 待填写 |
| structural_index | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | provider: none / graphify / codegraph / both；status: disabled / missing / enabled-fresh / enabled-stale / trial；freshness: fresh / stale / missing / unknown；reason: 待填写 | 待填写 |
| ship-check | not-needed / used | 待填写 | 待填写 |
| code_review | not-needed / micro-local-check / local-checklist / enhanced-review | 待填写 | 待填写 |
| task_closeout | not-needed / focused / strict-pass / strict-fail | validator / artifact / reason: 待填写 | 待填写 |
| docs_fact_drift | not-needed / checked / stale-found / blocked | validator / scan rows / reason: 待填写 | 待填写 |
| isolated_reviewer | not-needed / assessment-only / preferred / policy-auto-started / task-authorized-started / session-authorized-started / external-opt-in-started / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / budget-exceeded / explicit-denied | reason / packet / validator artifact / verdict / fallback: 待填写 | 待填写 |
| release_artifact_source_gate | not-needed / clean-source-build / source-manifest-build / allowed-diff-build / blocked | release-source packet / artifact sha256 / risk acceptance: 待填写 | 待填写 |
| trace_to_eval_intake | not-needed / candidate / recorded / deferred | source trace / fixture idea / validator gap / not-needed: 待填写 | 待填写 |
| red_team | not-needed / light / full | 待填写 | 待填写 |
| sensitive_guard | not-needed / warning / strict-block / reviewed | 待填写 | 待填写 |
| push_gate | not-needed / done / blocked | 待填写 | 待填写 |
| external_skill_intake | not-needed / catalog-only / repo-local / tooling-router / rejected / trial | 待填写 | 待填写 |

## Source Roots / Repos Touched
> 仅在多 git root、项目根不是 git root、跨 source root、release/external-system、Structural Index 查询或 CodeGraph 试点时填写；普通单仓 fast path 写 `not-needed`。稳定 root 清单以 `.agents/references/project-conventions.md#Source Root Registry` 为准，本表只记录本轮实际触碰和证据。
> `run_id`、`commit_ref`、`push_ref`、`source-file:<root_id>:<path>` 是不同证据类型；不要把 commit/push/source-file 写成 `Run Evidence.run_id`。

| root_id | repo_id | vcs_root | source_root | status | dirty_status | commit_or_ref | evidence_manifest | notes |
|---|---|---|---|---|---|---|---|---|
| not-needed / 待填写 | not-needed / 待填写 | not-needed / `.` / `subrepo` | not-needed / registry:<root_id> / `path` | not-needed / declared / touched / verified / blocked | clean / dirty / not-git / unknown / not-needed | commit-ref:<sha> / push-ref:<sha> / branch / not-needed | `.agent-state/runs/<run_id>/manifest.json` / not-needed | 待填写 |

## Trace-to-Eval Intake
> 真实任务暴露 workflow miss、漏触发、误触发、over-claim、reviewer 漏审或证据缺口时填写。这里只记录候选，不自动创建 eval、不进入默认 CI、不替代 `findings.md#Real Task Feedback Loop`。
> 需要判断机制效果时，必须标明 `task_epoch`、`mechanism_id`、`introduced_at`、`workflow_synced_at`、`applies_from` 和 `source_baseline`，避免用旧机制样本评判当前机制。
> 审计真实项目 workflow 效果前，先做 epoch preflight：机制 `introduced_at`、项目 workflow `workflow_synced_at`、任务 `started_at / updated_at / completed_at`、证据来源和 `audit_lens=active/submitted/archive`。`pre-mechanism / pre-sync` 只能写 `legacy`；同步窗口 / active task 迁移 / 跨版本证据写 `migration`；只有任务和证据都在机制生效后才写 `current`；时间线不清是 preflight `unknown`，不要落候选行，先补证据，不要把 `defer` 当成 `task_epoch` 值。
> Candidate rows must include `attribution_type`. `execution-lapse` means the agent failed to follow existing valid guidance; it is not evidence to rewrite skill/reference/template bodies. `eval-candidate` rows must carry a positive + negative fixture guard or point to an existing covering case.

| signal | source trace / artifact | audit_lens | attribution_type | expected behavior | observed behavior | task_epoch | mechanism_id | introduced_at | workflow_synced_at | applies_from | source_baseline | candidate eval type | eval guard | disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| not-needed / workflow miss / over-claim / reviewer-miss / validator-gap / evidence-gap | `.agent-state/runs/<run_id>/...` / progress / findings / none | active / submitted / archive / not-needed | not-needed / knowledge-gap / skill-defect / execution-lapse / validator-gap / reviewer-gap / tooling-gap / environment-debt / docs-drift / external-change / routing-gap / template-gap | 待填写 | 待填写 | legacy / migration / current / not-needed | gate / validator / reviewer policy / not-needed | mechanism commit/date/doc / not-needed | project sync commit/date / not-needed | task/run cohort; task updated_at / not-needed | current task / migration window / legacy archive / not-needed | behavior fixture / trajectory fixture / validator fixture / live-eval-experiment / not-needed | positive+negative+failure-oracle / already-covered:<case-id> / not-needed | none / eval-candidate / defer / already-covered |

## Structural Index Query Evidence
> 仅记录本轮结构索引查询摘要。CodeGraph / Graphify 输出不是事实源；`source_confirmed=no` 或 `source_confidence=index-candidate/stale-candidate/unknown` 的结果只能作为候选影响面，不能作为 PASS evidence、release evidence 或 reviewer final fact。
> `source_root_id` 必须对应 `.agents/references/project-conventions.md#Source Root Registry`；CodeGraph / Graphify freshness 是 per-root，不得用一个项目级状态代表所有 root。

| provider | status | decision | query_intent | source_root_id | source_root | root_freshness | query_count | summary_path | source_confirmed | source_confidence | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none / graphify / codegraph / both | disabled / missing / enabled-fresh / enabled-stale / trial | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | impact / callers / callees / affected-tests / symbol-search / not-needed | not-needed / registry:<root_id> | `待填写` / not-needed | fresh / stale / missing / unknown / not-needed | 0 / 1 / 3 / explicit | `.agent-state/runs/<run_id>/structural-index/...` / not-needed | yes / no / not-needed | source-confirmed / test-confirmed / index-candidate / stale-candidate / unknown / not-needed | 待填写 |

## Structural Index Pilot Effect
> 可选试点效果记录。只在本轮实际使用 Graphify / CodeGraph 辅助定位、显式试点或收集指标时填写；不是 PASS evidence、release evidence、默认 gate 或第二状态源。缺少本表不得阻断 fast path / low / ordinary standard 任务。
> `useful` 至少要有一个可复核收益信号：改变计划、发现相关源码 / 测试、避免错误修改或节省重复定位时间，且 `source_confirmed=yes`。`affected-tests`、`callers` 或 `callees` 为空只能记为 limitation signal，不能单独用来缩小测试范围。

| provider | decision | source_root | decision_changed | avoided_wrong_edit | tests_or_files_discovered | false_negative_or_empty_signal | elapsed_or_saved_time | artifact_size_or_cost | root_freshness | freshness_basis | roi_signal | roi_claim_status | source_confirmed | reindexRecommended | disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| none / graphify / codegraph / both | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | `待填写` / not-needed | yes / no / unknown / not-needed | yes / no / unknown / not-needed | tests / files / none / unknown / not-needed | affected-tests-empty / callers-empty / callees-empty / false-negative / none / unknown / not-needed | minutes saved / elapsed minutes / unknown / not-needed | low / medium / high / bytes / not-needed | fresh / stale / missing / unknown / not-needed | metadata / query-time / source-snapshot / not-needed | changed-plan / found-files / found-tests / avoided-wrong-edit / saved-time / none / not-needed | not-claimed / candidate / proven-positive / neutral / negative / not-needed | yes / no / not-needed | yes / no / unknown / not-needed | useful / neutral / costly / defer / not-needed |

## Review / Audit Boundary
> 审查、评估、核查、复盘、还原执行过程或“是否符合 workflow”类任务填写；默认只读。接受 finding 不等于授权实现。可用 `.agents/scripts/validate-review-authorization.py --strict-trigger` 检查。

| item | value |
|---|---|
| Mode | review-only / plan-only / report-write-only / implementation-authorized / not-needed |
| Write authorization | none / report-only / task / session / revoked / not-needed |
| Authorization source | user message / task instruction with active task / run_id / repo path / not-needed |
| Allowed write scope | repo/path/files / not-needed |
| Prohibited actions | deploy / commit / push / external-write / business-code-write / none |
| Finding disposition policy | accepted-as-finding-only / implementation-approved / not-needed |
| Transition decision | stay-readonly / report-write-only / ask-user / implement-authorized / not-needed |

## Run Evidence
> 记录本轮关键工具运行证据；日志和 JSON 摘要优先放在 `.agent-state/runs/<run_id>/`，不要把长日志直接粘贴到本文。
> 如存在 `.agent-state/runs/<run_id>/manifest.json`，优先引用 manifest；旧 `.agents/runs/<run_id>/...` 只做兼容读取。本文只保留摘要和链接。
> `Run ID` 只有在填入具体非占位 ID 时才表示顶层 run manifest；`Trace ID`、表头和 `optional / 待填写` 不会被当成 run manifest。
> manifest 的 duration/token/cost/redaction 等低税观测字段推荐填写；缺失默认只 warning，不阻断 fast path 或普通 standard 任务。
> 命令结果作为 high / release / external-system 或 strict closeout 的 PASS 证据时，优先用 `.agents/scripts/capture-run-command.py --run-id <run_id> -- <command...>` 捕获，并引用 manifest。

| run_id | trace_id | tool / command | status | manifest / artifact | notes |
|---|---|---|---|---|---|
| optional / 待填写 | optional / 待填写 | 待填写 | pass / fail / skipped / approval-required | `.agent-state/runs/<run_id>/manifest.json` / `.agent-state/runs/<run_id>/...` / none | 待填写 |

## Tool / Prompt / Command Contract Evidence
> 只有触发 Tool Invocation Contract / Prompt & Command Contract 时填写；普通只读搜索和 focused lint/test/build 可写 `not-needed`。这里记录结果，不替代 `Run Evidence` 或 `tooling-map.md`。
> 如果 trigger 是 `external-content-derived-command`，`artifact / evidence` 必须引用 `.agent-state/runs/<run_id>/external-content-boundary.json` 或等效边界 artifact，证明外部内容只被当作事实输入，不能授权命令、写入、部署、push、DB 或 secrets 访问。

| contract_id | trigger | exact literal preserved | authorization | result | artifact / evidence | stop condition hit | notes |
|---|---|---|---|---|---|---|---|
| not-needed / TIC1 | tool / prompt-snippet / command-contract / external-content-derived-command / high-risk-command | yes / no / not-needed | none / policy-auto-readonly / explicit-user / required | used / skipped / blocked / failed / not-needed | `.agent-state/runs/<run_id>/...` / not-needed | none / secret-suspected / timeout / permission-denied / packet-insufficient / not-needed | 待填写 |

## Verification Script Capture
> 临时脚本如果作为交付证据，必须复制到 `.agent-state/runs/<run_id>/scripts/`，并记录 command、sha256、输入和输出 artifact。

| script | captured path | sha256 | command | output artifact | status |
|---|---|---|---|---|---|
| not-needed / 待填写 | `.agent-state/runs/<run_id>/scripts/...` / none | 待填写 | 待填写 | 待填写 | captured / missing / not-needed |

## Acceptance Evidence
> 每个验收项至少对应一个证据；证据可以是命令、artifact、截图、trace、API 响应摘要或人工 QA 记录。

| acceptance item | scenario_id | case_class | evidence method | evidence location | result |
|---|---|---|---|---|---|
| 待填写 | not-needed / S1 / 待填写 | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | command / artifact / screenshot / trace / API response / manual note | 待填写 | pass / fail / waived / pending |

## Requirement Reconciliation
> 最终验收前把实现、测试和证据重新对回 `Requirement Contract`、`Negative Constraints`、`Behavior Scenarios` 和用户确认项。它不是第二套验收 ledger；只记录是否存在需求偏离。测试全绿但这里为 `mismatch` 或 `needs-human-check` 时，不得把相关验收项写成无条件 `PASS`。

| check_id | requirement_id / acceptance_id | scenario_id | compared sources | implementation / evidence checked | alignment_status | action / disposition | evidence |
|---|---|---|---|---|---|---|---|
| not-needed / RC1 | not-needed / A1 / R1 | not-needed / S1 | Requirement Contract / Negative Constraints / Behavior Scenarios / user answer / existing behavior / contract schema / not-needed | diff / test / artifact / manual review / not-needed | pass / mismatch / needs-human-check / waived / not-needed | accept / fix-before-ship / ask-user / waiver / not-needed | `.agent-state/runs/<run_id>/...` / manual note / not-needed |

## Manual Validation Checklist
> UI、浏览器、扩展、人工 QA 或无法稳定自动化的行为验证使用本表。它是 evidence artifact，不替代自动化测试；不需要时写 `not-needed`。

| manual_check_id | step | status | evidence | notes |
|---|---|---|---|---|
| not-needed / M1 | 待填写 | pass / fail / skipped / pending / not-needed | screenshot / trace / report / manual note / not-needed | 待填写 |

## Final Evidence Ledger
> 复杂任务 / release 收口时填写；把 Verification Matrix、补充脚本、人工 QA 和 waiver 合成唯一验收口径。
> 状态枚举需与 `.agents/scripts/workflow_routing.py` 的共享常量保持一致；模板保留可见选项是为了可靠填写，不代表另建枚举来源。
> `PASS` 的命令型证据必须引用 `.agent-state/runs/<run_id>/manifest.json` 或 durable run artifact；`manual note:` 只用于真正人工 QA / 外部人工确认，不能替代 `pytest`、`npm test`、`run-workflow-evals.sh`、`verify-workflow-smoke.sh` 等命令证据。人工验证优先写 `Manual Validation Checklist`，最终状态用 `MANUAL`。

| acceptance id | scenario_id | case_class | matrix status | supplemental evidence | final status | artifact | notes |
|---|---|---|---|---|---|---|---|
| not-needed / A1 | not-needed / S1 / 待填写 | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | PASS / MANUAL_RECHECK / MISSING / 待填写 | `.agent-state/runs/<run_id>/manifest.json` / artifact / screenshot / trace / API response / manual QA note / waiver / none | PASS / MANUAL / WAIVED / FAILED / BLOCKED / NOT_APPLICABLE | `.agent-state/runs/<run_id>/manifest.json` / `.agent-state/runs/<run_id>/...` / screenshot / trace / report / not-needed | 待填写 |

## Grill Check
> 仅 `high` / `release` 且需求、领域词汇、历史决策、权限、数据流或架构边界不清时填写；否则写 `not-needed`。

| check | result | notes |
|---|---|---|
| ambiguity clarified | pass / fail / not-needed / waived | 待填写 |
| domain / ADR conflict checked | pass / fail / not-needed / waived | 待填写 |
| negative constraints confirmed | pass / fail / not-needed / waived | 待填写 |
| user confirmation | approved / pending / not-needed / waived | 待填写 |

## Test Evidence Gate
> 普通 focused bugfix 可只记录“修复前复现 -> 修复后回归证据”的紧凑闭环；`high` / `release`、核心逻辑、跨层行为、权限 / 认证、字段契约、数据迁移或回归问题填写完整表。不能验证时写 waiver，不写“已测试”。

| requirement | coverage_type | evidence | result | waiver / notes |
|---|---|---|---|---|
| pre-fix reproduction | regression / failure-path / not-needed | failing test / command / API / browser / manual / not-needed | pass / fail / waived / pending | 待填写 |
| behavior / public-interface test | positive / boundary / negative / permission-deny / contract / not-needed | command / artifact / not-needed | pass / fail / waived / pending | 待填写 |
| end-to-end path evidence | compatibility / failure-path / release smoke / not-needed | API smoke / browser regression / integration / manual / not-needed | pass / fail / waived / pending | 待填写 |
| anti-overfit coverage | positive-plus-risk-case / parameterized examples / property-or-invariant / contract verification / golden-reviewed / waiver / not-needed | command / artifact / reviewer note / waiver | pass / fail / waived / pending | 待填写 |

### Red-Green / Anti-Overfit Evidence
> 选择 red-green、回归闭环、高风险缺陷、核心 / 跨层 / 权限 / 字段 / 迁移改动，或普通 bugfix 缺少明确修复前复现和修复后回归证据时填写完整表。普通 focused bugfix 已有 pre/post evidence 时可写 `not-needed`，避免把小修复拖进完整 TDD 表。

| scenario_id | pre-fix command | expected failing assertion | post-fix command | same scenario? | risk case covered | result / waiver |
|---|---|---|---|---|---|---|
| not-needed / S1 | failing test / reproduction command / not-needed | behavior missing / regression reproduced / invariant violated / not-needed | same test / focused regression / behavior smoke / not-needed | yes / no / not-needed | positive / boundary / negative / permission-deny / failure-path / contract / waiver / not-needed | pass / fail / waived / pending |

## Docs Fact Drift Check
> 当本轮实现了之前在 docs / tests / README / planning notes 中写成 future work、not implemented、planned、TODO、missing 或 disabled 的能力时填写。只写受影响的明确短语；不做全仓泛扫。不触发时写 `not-needed`。
> `scan_paths` 必须是项目根内 repo-local 文档/测试路径，不得使用 `..` 跳出项目根，不得使用 `.` / `**/*.md` 这类 repo-wide glob，也不得指向 `.agent-state`、`.agents/tasks`、Graphify / CodeGraph 输出、`node_modules`、`dist`、`build`、`coverage`、`.next`、`target`、缓存、日志或其他生成/运行/归档目录。`accepted-stale` / `deferred` 必须有证据或理由。

| implemented_capability | stale_phrase | scan_paths | disposition | evidence |
|---|---|---|---|---|
| not-needed / 待填写 | not-needed / exact phrase | docs/ / tests/ / README.md / not-needed | checked / not-needed / still-future-work / accepted-stale / deferred | command / artifact / commit / reason |

## Completed
- [x] 已完成事项 1

## In Progress
- [ ] 进行中事项 1

## Next
- [ ] 下一步 1

## Validation

### 已验证
| command / check | result | evidence | conclusion |
|---|---|---|---|
| 待填写 | 待填写 | command / artifact / manual note | 待填写 |

### 未验证
- 内容：待填写
- 原因：待填写
- 风险：待填写

## Changed Files Manifest
> `high` / `release` 任务必须填写；fast path 可标记为 `not-needed`。

| category | files / source | status | notes |
|---|---|---|---|
| repo / branch / base | not-needed / 待填写 | pending / checked | 真实 Git 边界、分支、基线；非 git 项目写明事实 |
| task-owned changes | 待填写 | pending / checked | 本任务实际修改的文件 |
| pre-existing dirty files | none / 待填写 | pending / checked | 执行前已存在或与本任务无关的脏文件 |
| generated artifacts | none / 待填写 | pending / checked | 构建产物、截图、压缩包、日志等 |
| deployment package | none / 待填写 | pending / checked | 发布包、备份、回滚点 |
| collaboration notes | none / 待填写 | pending / checked | 多人协作、子仓库、禁止触碰文件、未提交状态说明 |

## Dirty Worktree Summary
> commit / push 前填写；推荐用 `.agents/scripts/classify-worktree-dirty.py --format json` 或等效检查。无 git 仓库时写明事实。

| category | count | action | notes |
|---|---:|---|---|
| sensitive | 0 | excluded / reviewed / blocked / not-needed | `.env`、密钥、token、私钥等 |
| generated | 0 | excluded / reviewed / blocked / not-needed | 构建产物、日志、缓存、graphify-out、.codegraph、codegraph-out、数据库文件等 |
| workflow-state | 0 | included / excluded / reviewed / not-needed | `.agents`、`.codex`、三文件等 |
| source-or-doc | 0 | included / excluded / reviewed / not-needed | 本任务源代码或文档 |
| large | 0 | excluded / reviewed / blocked / not-needed | 大文件或部署包 |

## Diff-to-Plan
> 收口或 review 时填写；检查实际 diff 是否越过 `task_plan.md` 的 Scope、Negative Constraints 和 Execution Table。

| check | result | notes |
|---|---|---|
| changed files within planned scope | pass / fail / not-needed | 待填写 |
| negative constraints respected | pass / fail / not-needed | 待填写 |
| unexpected files explained | pass / fail / not-needed | 待填写 |

## Red-team Review
> push 前或 `high` / `release` 任务收口时填写；非代码或无行为变化可写 `not-needed`。

| dimension | result | notes |
|---|---|---|
| 需求偏离 / scope creep | pass / fail / not-needed | 待填写 |
| 边界条件 / 失败路径 | pass / fail / not-needed | 待填写 |
| 权限 / 安全 / 数据隔离 | pass / fail / not-needed | 待填写 |
| 数据一致性 / 回滚 | pass / fail / not-needed | 待填写 |
| 架构边界 / 依赖方向 | pass / fail / not-needed | 待填写 |
| WSL / Windows / 路径 | pass / fail / not-needed | 待填写 |
| 测试缺口 / 验证豁免 | pass / fail / not-needed | 待填写 |
| 协作风险 / 生成物污染 | pass / fail / not-needed | 待填写 |

## Release S0/S1 Red-team
> `release` / `external-system` 必填；不强制外部 reviewer，但必须完成本地 S0/S1 检查。

| check | result | notes |
|---|---|---|
| 权限 / 认证反向验证 | pass / fail / not-needed / waived | 待填写 |
| 生产配置误改 | pass / fail / not-needed / waived | 待填写 |
| 数据库 / 缓存 / 队列回退点 | pass / fail / not-needed / waived | 待填写 |
| tracked `.env` / runtime data | pass / fail / not-needed / waived | 待填写 |
| release artifact 可复现 | pass / fail / not-needed / waived | 待填写 |
| blocking verification / rollback point | pass / fail / not-needed / waived | 待填写 |

## Release Artifact Source Gate
> `release` 或 `external-system` 构建 jar / dist / container / 部署包时填写。工作区不干净时，部署前必须有 source evidence；不适用写 `not-needed`。

| item | value |
|---|---|
| Required | yes / no |
| Source mode | clean-source-build / source-manifest-build / allowed-diff-build / blocked / not-needed |
| Release-source packet | `.agent-state/runs/<run_id>/release-source/` / not-created / not-needed |
| Base commit / branch | 待填写 |
| Artifact | jar / dist / container / package / not-needed / 待填写 |
| Artifact sha256 | `.agent-state/runs/<run_id>/release-source/artifact-sha256.txt` / 待填写 |
| Clean source evidence | `git status --short` clean transcript / `.agent-state/runs/<run_id>/release-source/git-status-clean.txt` / not-needed / 待填写 |
| Intended source files | `.agent-state/runs/<run_id>/release-source/intended-source-files.json` / not-needed / 待填写 |
| Dirty source count | 0 / 待填写 |
| Legacy allowed source scope | compatibility-only: `.agent-state/runs/<run_id>/release-source/allowed-source-scope.txt` / not-needed / 待填写 |
| Unrelated dirty source disposition | excluded / reviewed / blocked / not-needed / 待填写 |
| Ship-check / reviewer confirmation | pass / fail / waived / not-needed / 待填写 |
| Explicit user risk acceptance | none / required / accepted |
| Attestation mode | local-only / github-attested / slsa / npm-provenance / not-needed |
| Attestation verification | not-run / pass / fail / skipped-with-reason / not-needed |
| Attestation artifact | `.agent-state/runs/<run_id>/release-source/attestation.*` / not-needed / 待填写 |

## Isolated Reviewer
> Legacy-compatible heading for validator support; semantically this is the Role Reviewer assessment. New prose should use `Role Reviewer`.

> 仅在明确要求只读挑战，或确定性验证后仍有具体 residual semantic risk 时填写本节。high/release 单独不要求。未触发可省略整节或写 `not-needed`。这是条件增强项，不是默认启动 gate。

| item | value |
|---|---|
| Required assessment | yes / no |
| Trigger decision | not-needed / assessment-only / preferred |
| Reason | risk / external-system / auth / DB / deploy / rollback / waivers / dirty-worktree / long-session / not-triggered |
| Authorization scope | none / policy-auto / task / session / external-standing-opt-in / revoked |
| Authorization source | AGENTS.md Policy-Auto Reviewer / user message / task instruction / external standing opt-in / not-needed |
| Start required | yes / no / not-needed |
| Runtime policy status | not-checked / allowed / runtime-policy-blocked / explicit-delegation-required / explicit-denied / revoked / not-needed |
| Start result | not-needed / policy-auto-started / task-authorized-started / session-authorized-started / external-opt-in-started / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / budget-exceeded / explicit-denied |
| Reviewer tool | Codex subagent / Gemini / Claude / other / unavailable / runtime-policy-blocked / not-needed |
| Model policy | inherit-main-model / external-reviewer / not-needed |
| Reasoning effort | xhigh / inherited / not-needed |
| Timeout policy | review-incomplete / reviewer-timeout / not-needed |
| Runtime-enforced budget | hard-timeout / hard-turn-limit / hard-file-limit / prompt-soft-limit / manual-fallback / not-needed |
| Input package | `.agent-state/runs/<run_id>/role-review/<role>/` / legacy `.agent-state/runs/<run_id>/isolated-review/` / not-created / not-needed |
| Packet validator status | pass / fail / not-run / not-needed |
| Packet validator command | `.agents/scripts/validate-role-review-packet.py --root . --packet ... --risk-tier high --format json` / not-needed |
| Packet validator exit code | 0 / nonzero / not-needed |
| Packet validator artifact | `.agent-state/runs/<run_id>/role-review/<role>/packet-validator.json` / not-needed |
| Review focus | quality / security / test-coverage / release-risk / mixed / not-needed |
| Secret handling | redacted / metadata-only / not-needed |
| Verdict | pass / needs-more-evidence / blocking / review-incomplete / review-unverified / not-needed |
| Disposition | accepted / rejected / needs-more-evidence / deferred / not-needed |
| Fallback | local S0/S1 red-team / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / explicit-denied / not-needed |

## Reviewer Start Authority
> `policy-auto` 是 G16 已路由后内部只读 reviewer 的项目级 start authority；当前仅对 high / release / external-system 任务开放。档位本身不触发 assessment、不优先 reviewer、不构成启动理由。它不能覆盖系统 / 开发者 / 工具调用政策。外部模型 reviewer、写入型 worker、deploy / DB write / push / external-write、secrets 访问、超过 reviewer 数量上限，仍必须用户明确授权。授权只对当前 active task / run_id / repo path 有效，任务切换、目标路径变化、权限扩大、跨会话恢复或进入 external-write 时自动失效。`Scope=implementation-worker` 不是 Role Reviewer 的一种；默认不存在，只有用户另行授权且写入范围隔离时另案启用。`Authorized roles` 指本次授权覆盖的挑战焦点，不是编制；新 Brief 推荐 `requirements` / `security` / `release`，其余 token 仅兼容。

| item | value |
|---|---|
| Authority mode | policy-auto / task-authorized / session-authorized / external-standing-opt-in / not-needed |
| Authority source | AGENTS.md Policy-Auto Reviewer / user message / task instruction / external standing opt-in / not-needed |
| Scope | read-only reviewer / implementation-worker / external-write / not-needed |
| Active task id | `<task_id>` / not-needed |
| Run ID | `<run_id>` / not-needed |
| Repo path | 待填写 / not-needed |
| Authorized roles | requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed / not-needed |
| Max reviewers | 0 / 1 / 2 / explicit-budget / not-needed |
| External model allowed | no / yes-with-standing-opt-in / not-needed |
| Expires | active task completion / target path change / permission expansion / cross-session recovery / external-write / not-needed |
| Runtime policy status | not-checked / allowed / runtime-policy-blocked / explicit-delegation-required / explicit-denied / revoked / not-needed |
| Runtime-enforced budget | hard-timeout / hard-turn-limit / hard-file-limit / prompt-soft-limit / manual-fallback / not-needed |

## Role Review Summary
> 仅在启动 isolated reviewer 或其他只读风险 reviewer 后填写；一行一个 reviewer role，只记录已启动或明确 assessment 的角色；不创建第二套 plan / progress / handoff。`role` / `Authorized roles` 指本次授权覆盖的挑战焦点，不是编制。新 Brief 推荐 `requirements` / `security` / `release`；其余 token 仅兼容。

| role | trigger | packet | focus | verdict | disposition | unresolved risk |
|---|---|---|---|---|---|---|
| not-needed / requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed | 待填写 | `.agent-state/runs/<run_id>/role-review/<role>/` / legacy `.agent-state/runs/<run_id>/isolated-review/` / not-needed | quality / security / test-coverage / release-risk / knowledge-promotion / mixed | pass / needs-more-evidence / blocking / incomplete / not-needed | accepted / rejected / needs-more-evidence / deferred / not-needed | none / 待填写 |

## Reviewer Calibration Summary
> 只在启动 reviewer 或做多视角审查实验后填写。记录 reviewer 的可观察信号和流程税，不作为质量 PASS、交付 PASS 或真实项目收益声明；真实收益需要 accepted finding rate、返工、漏检、耗时和 token/cost 趋势等后续指标支撑。不要求 fast path 填写。

| role | started | findings_total | accepted | rejected | needs_more_evidence | evidence_levels | incomplete_or_timeout | plan_changed? | notes |
|---|---|---:|---:|---:|---:|---|---|---|---|
| not-needed / requirements / qa / security / release / mixed | yes / no / not-needed | 0 | 0 | 0 | 0 | direct:0 indirect:0 unverified:0 | none / review-incomplete / reviewer-timeout / runtime-policy-blocked / not-needed | yes / no / not-needed | signal / cost / changed_plan / false_positive / 待填写 |

## Review Finding Closure Map
> review、Gemini、子 agent、第三方专家或本地 red-team finding 被接受后，用本表追踪到修复证据。没有 review finding 时写 `not-needed`。

| finding_id | source | disposition | linked_acceptance_id | linked_scenario_id | linked_slice_id | case_class | fix evidence / commit | verification evidence | status |
|---|---|---|---|---|---|---|---|---|---|
| not-needed / F1 | code_review / role-review / Gemini / third-party / local-red-team | accepted / rejected / needs-more-evidence / deferred / not-needed | A1 / not-needed | S1 / not-needed | slice-1 / not-needed | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | commit:<sha> / changed-files / not-needed | command / artifact / manual note / not-needed | open / fixed / verified / waived / not-needed |

## Sensitive Operations
> 没有则写 `none`；有则说明命令意图、影响范围、确认状态和回退点。

| operation | risk | confirmation | rollback / mitigation |
|---|---|---|---|
| none / 待填写 | 待填写 | not-needed / pending / approved | 待填写 |

## Verification Waivers
> 只有必需验证失败、超时、不可运行或被替代验证覆盖时填写；没有则写 `none`。

| check | reason | substitute evidence | allowed to ship | owner / follow-up |
|---|---|---|---|---|
| none / 待填写 | 待填写 | 待填写 | yes / no / conditional | 待填写 |

## Active Task Migration Check
> 仅在同步 / 升级 starter-pack、workflow 模板、validators、skills 或 hooks 后，当前三文件仍是 active complex/high/release 任务时填写；否则写 `not-needed`。

| item | value |
|---|---|
| Required | yes / no |
| Trigger | workflow-sync / validator-upgrade / template-upgrade / skill-upgrade / hook-upgrade / not-needed |
| Validator | `.agents/scripts/validate-active-task-migration.py` / manual / not-needed |
| Result | pass / fail / waived / not-needed |
| Migrated items | Phase Change / Behavior Scenarios / scenario_id / Final Evidence Ledger / Isolated Reviewer / none |
| Waiver / owner | none / 待填写 |

## Tooling Gaps
> `high` / `release` 任务中，匹配工具 disabled / missing / skipped / approval-required 时填写；没有则写 `none`。

| tool class | status | reason | substitute evidence | owner / follow-up |
|---|---|---|---|---|
| none / secret-scan / dependency-scan / sast / semantic-search | disabled / missing / skipped / approval-required / not-needed | 待填写 | 待填写 | 待填写 |

## Tooling Gap Debt
> `high` / `release` 或同类 waiver 重复出现时填写；普通任务可写 `none`。

| tool class | gap | first seen | repeat count | owner | alternative evidence | due / refresh when | status |
|---|---|---:|---:|---|---|---|---|
| none / secret-scan / dependency-scan / block-tool | 待填写 | 待填写 | 0 | 待填写 | 待填写 | 待填写 | open / deferred / closed |

## External Skill Intake
> 外部 skill catalog 只作为候选来源；没有引入时写 `not-needed`。
> 语义供应链风险包括 trigger stuffing、governance evasion、permission laundering 和 description-only selection bias；这些只能触发 `human-needed` 或降级，不授权安装 / 启用 / 写入。

| candidate | decision | source / trust | reason | permissions / data exposure | semantic risk | boundary / owner |
|---|---|---|---|---|---|---|
| none / 待填写 | catalog-only / repo-local / tooling-router / rejected / trial | official / standard / paper / community / unknown | 重复 / 权限 / 验证 / 项目需要 / 待填写 | none / repo-read / repo-write / external-read / external-write / network / token | semantic_risk / trigger_stuffing / governance_evasion / permission_laundering / not-needed | not-needed / 待填写 |

## Local Skill Promotion / Update Assessment
> 只做评估，不自动创建 / 更新 / 推广 skill。`recommend-create` / `recommend-promote` 不是授权。

| item | value |
|---|---|
| Decision | none / candidate / update-needed / recommend-create / recommend-promote / defer |
| Skill | not-needed / `.agents/skills/<name>/SKILL.md` / 待填写 |
| Reason | repeated SOP / release-deploy / review gap / known-bad path / facts changed / not-needed / 待填写 |
| Evidence | `.agent-state/runs/<run_id>/...` / findings / progress / none |
| Next action | no action / ask user authorization / update references first / run skill-creator / validate-local-skills / de-projectization check / defer |

## Human Decision Surface
> 当没有专用 closeout section 的派生报告、gate、review 或风险评估要求人工判断时填写；这是主动向用户抛 bounded question / disposition 的记录，不是授权、不是 backlog、不是第二状态源。
> 已有专用 surface 的机制继续使用专用 section，例如 `Skill Curator Closeout`；不要重复填两张表。
> `record-only` 只记录；`surface-required` 必须在最终回复或 closeout 主动抛出；`answer-required` / `risk-acceptance-required` 没有用户明确回答时不得执行对应动作。

| decision_id | source | level | surfaced | default recommendation | options | disposition | authorization scope | evidence |
|---|---|---|---|---|---|---|---|---|
| not-needed / HD-YYYYMMDD-01 | workflow-value-report / release-source / review-boundary / requirement-reconciliation / external-skill / sensitive-operation / other-derived-report | record-only / surface-required / answer-required / risk-acceptance-required | not-needed / yes / asked-user / recorded / deferred / rejected / user-approved | conservative default; usually record-only, defer, narrow-trigger, or ask-user | A recommended option; B alternative; C stop/defer | record-only / ask-user:<question> / reject:<reason> / defer:<reason> / user-approved-scope:<scope> | none / repo-local / specific file paths / explicit user scope | `.agent-state/runs/<run_id>/...` / progress / findings |

## Skill Curator Closeout
> 仅当引用 `.agent-state/runs/<run_id>/skill-evolution/curator-report.json` 且报告含 `human_needed` 时填写；这是主动向用户抛 bounded question / disposition 的记录，不是授权自动创建、更新、安装、启用或全局化 skill/plugin。

| item | value |
|---|---|
| Curator report | not-needed / `.agent-state/runs/<run_id>/skill-evolution/curator-report.json` |
| Human-needed surfaced | not-needed / yes / asked-user / recorded / deferred / rejected / user-approved |
| Human-needed items | none / item names |
| Question / disposition | record-only / ask-user:<question> / reject:<reason> / defer:<reason> / user-approved-scope:<scope> |

## Defect Status
> 仅在 bugfix、回归、测试失败、生产问题或用户可复现异常时填写；非缺陷任务可写 `not-needed`。

| defect_id | current status | closure evidence | allowed to ship | owner / follow-up |
|---|---|---|---|---|
| not-needed / DEF-YYYYMMDD-01 | open / triaged / fixing / fixed / verified / no-repro / waived / closed | command / artifact / manual note / pending | yes / no / conditional | 待填写 |

## Environment Debt Status
> 已知坏环境有稳定替代方案时填写；生产开发 / 发布交付阶段默认走稳定替代方案，不顺手修环境。没有稳定替代方案时写 `blocker`。

| bad environment / path | stable workaround | current policy | repair trigger | owner / follow-up | status |
|---|---|---|---|---|---|
| none / 待填写 | 待填写 | use workaround / blocked / not-needed | user-approved env fix / workaround failed / scheduled maintenance / 待填写 | 待填写 | not-needed / recorded / missing / blocker / closed |

## Context Compaction
> 长任务、release 任务或出现 compact / 上下文失败时填写；普通短任务可写 `not-needed`。
> 归档 / compact 摘要是 reference-only，不是当前任务指令；不要把旧用户请求、旧计划或旧 reviewer finding 当作当前 active task。

| trigger | status | action |
|---|---|---|
| findings/progress 膨胀 | not-needed / needed / done | 待填写 |
| 阶段切换 / handoff | not-needed / needed / done | 待填写 |
| remote compact failure / context overflow | not-seen / seen | 待填写 |
| archived summary path | none / 待填写 | 待填写 |

## Browser / UI Evidence
> `release` 级 UI / 浏览器改动必须填写；非 UI 任务可标记为 `not-needed`。

| evidence | path / command | result | notes |
|---|---|---|---|
| not-needed / screenshot / trace / report / CDP check | 待填写 | pass / fail / skipped | 待填写 |

## Reboot Check
| question | answer |
|---|---|
| 当前在哪个阶段？ | 待填写 |
| 当前目标是什么？ | 待填写 |
| 当前范围 / 禁止项是什么？ | 待填写 |
| 已经学到什么？ | 待填写 |
| 已经完成什么？ | 待填写 |
| 下一步是什么？ | 待填写 |
| 下一步验证是什么？ | 待填写 |

## Handoff
- 当前阶段：待填写
- 已完成：待填写
- 正在做：待填写
- 下一步：待填写
- 必须先读的文件：待填写
- 继续前重述：active task id / 目标 / 范围 / 禁止项 / 下一步验证 / 未解决风险
- 归档建议：完成后复制三文件到 `.agents/tasks/YYYYMMDD-short-slug/`
- 归档状态：not-archived / archived-at `.agents/tasks/YYYYMMDD-short-slug/`
- 当前最大风险：待填写
