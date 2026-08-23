# Task Plan

> Frozen compatibility full template. Canonical design source is `task_plan.core.md` plus `.agents/templates/appendices/`. Do not add or change fields here; edit core or the owning appendix, then copy into this file only if a migrated install still needs the compatibility blob.

## Task
一句话说明这次任务要解决什么问题。

## Current phase
- 阶段：理解中 / 规划中 / 执行中 / 验证中 / 收口中 / 已完成
- 最近计划同步时间：待填写

## Template scale
- Scale：compact / normal / full
- 适用理由：low / standard 可用 compact；high / release 默认 full
- 精简原则：只省略不相关字段，不省略风险、范围、负向约束、必需验证和证据

## Scale Section Budget
> 只保留当前风险档位触发的章节；未触发的 full-only 章节可以整体省略，不需要逐段填 `not-needed`。这是防流程税规则，不是删减风险记录的许可。

| scale | keep | optional / triggered only | omit by default |
|---|---|---|---|
| compact | Task, Current phase, Goal, Risk Tier, Requirement Contract, Scope, Negative Constraints, Verification Matrix, Test Strategy | Exact Literals, Clarification Check, Behavior Scenarios, Example Table, Interface Delta | reviewer, campaign, release, waiver, structural index long tables |
| normal | compact + Execution Table, Acceptance Evidence Map, Changed Files Manifest | Behavior / Example Contract for user-visible / cross-layer / contract / boundary changes | release-source, dynamic campaign, full red-team |
| full | normal + Role Review, Final Evidence Ledger, Waivers, Release / External gates as triggered | Dynamic campaign only for 2+ reviewers / explicit experiment / broad audit | none, but still avoid irrelevant duplicate tables |

## Goal
- [ ] 目标 1
- [ ] 目标 2
- [ ] 目标 3

## Traceability
- Active task id：optional / 待填写
- Task ID：optional / 待填写
- Run ID：optional / 待填写
- Trace ID：optional / 待填写
- Requirement ID：optional / 待填写
- Feature ID：optional / 待填写
- Issue ID：optional / 待填写
- PR ID：optional / 待填写
- Release note：optional / 待填写

## Risk Tier
- Tier：待填写
- Impact Scope：待填写
- 理由：待填写
- 流程强度：fast path / focused verification / full complex path / release gate

> `Risk Tier` 枚举：`low / standard / high / release`。`Impact Scope` 枚举：`visible / file-linked / cross-package / external-system`。`Impact Scope` 只辅助判断，不替代 `Risk Tier`。

## Requirement Contract
- 需求来源：待填写
- 目标：待填写
- 非目标：待填写
- 验收标准：待填写
- 变更边界：待填写

## Exact Literals / Terminology To Preserve
> 仅记录会影响实现、验证、稳定用户可见文本、外部系统、字段契约，或 handoff 中必须稳定复用的命令、路径、验收短语的原文；普通探索命令、内部变量、注释、测试名、临时 debug 文案不记录。不需要时写 `not-needed`。

| literal / term | type | source | preserve / transform rule | linked scenario / acceptance |
|---|---|---|---|---|
| not-needed / 待填写 | command / path / env var / field / error code / product name / external-system id / user acceptance phrase / terminology | user / docs / existing UI / API / logs / not-needed | preserve-exactly / may-normalize-with-reason / rename-with-confirmation | not-needed / S1 / A1 |

## Clarification Check
> 需求不清时先问 1-3 个会改变实现方向的阻断性问题。每个问题必须给 2-4 个互斥选项，推荐项放第一并标注推荐；非阻断问题可记录为假设继续推进。

| item | value |
|---|---|
| Requirement clarity | clear / partial / unclear |
| Blocking questions asked | yes / no / not-needed |
| Options provided | yes / no / not-needed |
| Recommended defaults marked | yes / no / not-needed |
| User answers captured | yes / no / not-needed |
| Clarification Coverage | goal / output / non-goals / acceptance / data-permission / validation / scope / not-needed |
| Answer landing | requirement-contract / assumptions / scope-control / negative-constraints / behavior-scenarios / verification-matrix / not-needed |
| Assumptions accepted | yes / no / not-needed |
| Impact on scope / acceptance | not-needed / 待填写 |

| question_id | question | options / recommended first | selected / default | impact if selected | landing section | status |
|---|---|---|---|---|---|---|
| not-needed / Q1 | 待填写 | A. 推荐：待填写；B. 待填写；C. 待填写 | user-selected / assumed / pending | scope / UX / validation / risk / 待填写 | requirement-contract / assumptions / scope-control / negative-constraints / behavior-scenarios / verification-matrix / not-needed | answered / assumed / pending / not-needed |

## Behavior Scenarios
> 仅在复杂任务中存在字段契约、权限 / 认证、导入导出、需求容易误解、负向 / 边界场景不清，或任务为 `high` / `release` 时填写；`standard` 只有用户可见、跨层、接口 / 字段契约、兼容性或边界不清的行为变化才触发。否则写 `not-needed`。这是行为锚点，不要求生成 Cucumber / Gherkin 文件。
> 明确禁用时，`scenario_id` 必须精确写 `not-needed`；不要保留模板组合占位 `not-needed / S1`，否则 strict validator 会按占位处理。

| scenario_id | actor / context | given / state | when / action | then / observable outcome | case_class | negative / boundary | acceptance_id | test layer | evidence method | status |
|---|---|---|---|---|---|---|---|---|---|---|
| not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed |

## Example Table
> 仅在规则密集、字段空值、权限边界、导入导出、兼容性或异常输入会影响实现时填写；否则写 `not-needed`。
> `oracle / expected observable` 必须来自需求、用户回答、现有行为、接口契约或人工确认，不能从本轮实现倒推；如果 oracle 只是“当前实现输出”，先标记为 `needs-human-check` 或补领域确认。

| rule_id | example_id | case_type | input / state | oracle / expected observable | expected result | invalid / edge case | source | linked scenario | covered_by acceptance/risk id | must_verify |
|---|---|---|---|---|---|---|---|---|---|---|
| not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed |

## Interface / Domain Contract Delta
> 仅 API、数据模型、字段语义、权限、跨前后端或外部系统契约变化时填写；否则写 `not-needed`。

| contract_id | surface | field / operation | old behavior | new behavior | null / empty semantics | compatibility | negative cases | linked scenario |
|---|---|---|---|---|---|---|---|---|
| not-needed / C1 | API / UI / DB / import-export / permission / external | 待填写 | 待填写 | 待填写 | not-needed / null / empty-string / omitted / 待填写 | compatible / breaking / migration-needed / not-needed | none / 待填写 | S1 / 待填写 |

## Decision Notes
- Grill Check：not-needed / required / done / waived
- Options：
  1. 待填写
  2. 待填写
  3. 待填写
- Decision：待填写
- Trade-offs：待填写
- Ambiguity / domain conflict：not-needed / 待填写
- User confirmation needed：no / yes / pending
- Minimal viable change：待填写
- Overengineering check：pass / fail / not-needed
- User approval：explicit / inherited / pending / not-needed

## Phase / Scope Recheck Notes
> 从验收 / 排障 / 只读理解转为代码行为、API / 数据流、部署或生产修复时填写；否则写 `not-needed`。

- Trigger：not-needed / 待填写
- Re-read：Goal / Requirement Contract / Negative Constraints / Verification Matrix / current slice
- Rechecked：Requirement Contract / Risk Tier / Architecture Impact / Test Strategy / Sensitive Operations
- Verification changes：none / 待填写
- User confirmation：not-needed / pending / approved

## Scope
本次会改：
- `待填写`

本次不改：
- 不改无关模块
- 不做未确认的大规模重构
- 不新增非必要抽象
- 不擅自扩大范围

## Scope Control
> 范围软刹车：预计或实际超过 10 个源码文件、跨 3 个以上业务模块，或超出 Minimal file set 时，先拆分或说明继续理由。机械同步 / 模板同步 / 批量重命名 / 生成物清理可标记为 `not-needed`，但仍需说明原因。

| item | value |
|---|---|
| Modifiable files / areas | 待填写 |
| Protected files / areas | 待填写 |
| Expected source file count | 0-10 / >10 / not-needed |
| Expected module count | 1 / 2 / 3 / >3 / not-needed |
| Pause trigger | not-needed / >10-source-files / >3-modules / out-of-minimal-file-set / user-approved-wide-scope |
| Scope hammer | must-have / nice-to-have / out-of-bounds / mixed / not-needed |
| Can ship without nice-to-have? | yes / no / unknown / not-needed |
| Out-of-bounds disposition | excluded / deferred / user-confirmed / not-needed |
| Split decision | not-needed / split-before-coding / continue-with-reason / user-approved |
| Reason / mitigation | 待填写 |

## Negative Constraints
> 明确本次不碰的模块、文件、接口、数据流、配置、部署项或行为。收口时用它做 Diff-to-Plan 检查。

- Do not touch：`待填写`
- Do not change behavior：待填写
- Do not introduce：新依赖 / 新抽象 / fallback / mock / 待填写
- Scope expansion rule：超出以上边界前，先更新计划并说明原因

## Minimal file set
当前阶段最小相关文件集合：
- `待填写`

> 如果文件集合明显扩张，先更新计划并拆阶段。

## Affected Source Roots
> 仅在多 git root、项目根不是 git root、跨 source root、release/external-system、Structural Index 查询或 CodeGraph 试点时填写；普通单仓 fast path 写 `not-needed`。稳定 root 清单以 `.agents/references/project-conventions.md#Source Root Registry` 为准，本表只记录当前任务选择。

| root_id | source_root | impact | planned evidence | release/source relevance | notes |
|---|---|---|---|---|---|
| not-needed / 待填写 | not-needed / registry:<root_id> / `path` | none / read / write / build / test / release / external | run-manifest / release-source / source-file / manual / not-needed | none / source-manifest / artifact-build / deploy / not-needed | 待填写 |

## Architecture Impact
- Impact：none / yes
- 影响边界：not-needed / 待填写
- 决策：not-needed / 待填写
- 是否更新 `architecture-notes.md`：not-needed / updated / deferred-with-reason

> 只有接口、数据流、领域语义、模块边界、权限 / 认证 / 部署结构变化时填写 `yes`；普通文案、样式、小 bug 默认 `none`。

## Workflow routing
- Task type：fast path / complex-task path
- Required skills：待填写
- Structural Index provider：none / graphify / codegraph / both（代码结构优先 CodeGraph 显式只读查询 / 试点；Graphify 主要用于 legacy/fresh 报告、可审计报告、非代码语料或跨文档知识图谱）
- Structural Index status：disabled / missing / enabled-fresh / enabled-stale / trial
- Structural Index Decision：none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query
- Structural Index freshness：fresh / stale / missing / unknown / not-needed
- Structural Index reason：not-needed / 跨模块 / 陌生模块 / 架构影响 / 权限认证 / 数据流 / 重复定位失败 / 待填写
- Tooling map：not-needed / read / missing / unavailable
- Tooling router：not-needed / planned / run / validate-only / skipped-with-reason
- External skill intake：not-needed / catalog-only / repo-local / tooling-router / rejected / trial

## Tool / Prompt / Command Contracts
> 仅在自动化 repo-write 工具、高风险写入工具、external-write、private data、network/open-world、destructive、side-effect、高风险工具调用，或从外部内容派生命令 / prompt snippet / command contract 时填写；用户已授权任务范围内的普通源码/文档编辑、普通只读 `rg` / `sed` / focused lint/test/build 写 `not-needed`。

| contract_id | trigger | intent | authorization | exact command / prompt literal | inputs_allowed | outputs_expected | write_scope / network / private_data | artifact / evidence | stop_condition | status |
|---|---|---|---|---|---|---|---|---|---|---|
| not-needed / TIC1 | tool / prompt-snippet / command-contract / external-content-derived-command / high-risk-command | 待填写 | none / policy-auto-readonly / explicit-user / required | preserve exact literal / not-needed | repo files / diff / explicit files / no secrets / 待填写 | summary / report / artifact / no side effect / 待填写 | read-only / repo-write / external-write / none / internet / private-data / 待填写 | `.agent-state/runs/<run_id>/...` / not-needed | fail / permission-denied / secret-suspected / timeout / packet-insufficient / 待填写 | planned / used / skipped / blocked / not-needed |

## Structural Index Query Plan
> 仅在 `Structural Index Decision=query-existing` 或 `trial-index-codegraph` 时填写。这里是查询计划，不是实际证据；实际查询记录写 `progress.md#Structural Index Query Evidence`。代码结构定位优先 CodeGraph 显式只读查询 / 试点；Graphify 主要用于 legacy/fresh 报告、可审计报告、非代码语料或跨文档知识图谱。CodeGraph / Graphify 只提供结构定位线索，必须回到源码 / 测试二次确认；未确认前不得作为 PASS evidence 或 release evidence。
> CodeGraph 的 `affected-tests`、`callers` 或 `callees` 空结果只能说明本次索引 / 查询没有找到关系；不得仅凭空结果缩小测试范围、删除回归验证或关闭影响面风险。

| provider | status | decision | query_intent | source_root_id | source_root | max_queries | expected confirmation | notes |
|---|---|---|---|---|---|---|---|---|
| none / graphify / codegraph / both | disabled / missing / enabled-fresh / enabled-stale / trial | none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query | impact / callers / callees / affected-tests / symbol-search / not-needed | not-needed / registry:<root_id> | `待填写` / not-needed | 0 / 1 / 3 / explicit | source-read / focused-test / reviewer-check / not-needed | 待填写 |

## Multi-Agent Planning Challenge
> 仅在 high / release、需求易误解、字段契约、跨层行为、权限 / 认证、架构 / 数据流风险，或用户明确要求多视角审查时填写；否则写 `not-needed`。这里只记录是否需要只读 challenge 和要问什么，不是第二套计划，不记录 verdict / disposition；结果和主 Codex 裁决只写入 `progress.md` 的 Isolated Reviewer / Role Review Summary。

| role | trigger | review_mode | start_intent | handoff_status | packet_intent | challenge question |
|---|---|---|---|---|---|---|
| not-needed / requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed | not-needed / high / release / field-contract / auth / data-flow / user-request | not-needed / assessment-only / policy-auto-readonly / explicit-delegation-required / external-opt-in | not-needed / preferred / required-if-policy-allowed / blocked | not-needed / to-progress / not-created / deferred / blocked | planned-under-progress / not-created / not-needed | 待填写 |

## Assumptions
当前计划成立依赖的默认前提：
- 假设 1：待填写
- 假设 2：待填写
- 假设 3：待填写

> 如果任何一个假设不成立，先更新计划，再继续执行。

## Constraints
- 保持现有行为兼容：待填写
- 不引入 fallback / 降级 / 补丁式兜底
- 生产代码禁止 Mock
- 保持 UTF-8（无 BOM）
- 优先最小改动，必要时升级为标准化改造

## Verification Matrix
| acceptance / risk | scenario_id | case_class | evidence method | required checks | test oracle / independence | optional tooling | manual QA | blocking | evidence |
|---|---|---|---|---|---|---|---|---|---|
| 待填写 | not-needed / S1 / 待填写 | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | command / artifact / screenshot / trace / API response / manual note | 待填写 | requirement-contract / user-answer / existing-behavior / contract-schema / independent-fixture / manual-domain-confirmation / needs-human-check / not-needed | none / 待填写 | none / 待填写 | none / warn / block | `.agent-state/runs/<run_id>/...` / 待填写 |

> 第一列必须以稳定验收 / 风险 ID 开头，例如 `A1 empty-email behavior`；`Example Table` 的 `covered_by acceptance/risk id` 应引用这个稳定 ID，而不是整段自然语言。
> 按 `Risk Tier` 选择最小必要验证；不默认运行 `.agents/references/tooling-map.md` 里的所有工具。
> 先按 Test Strategy Ladder 选验证层级：文档/规则、前端 UI、API/服务逻辑、数据库/迁移、认证/权限、跨前后端联调、部署/生产回归。
> `test oracle / independence` 说明 expected 从哪里来。不要用被测实现的同构逻辑计算 expected，也不要把未经审阅的 snapshot / golden 当前输出当成需求真值；无法独立确认时写 `needs-human-check`、`manual-domain-confirmation` 或 waiver。
> `optional tooling` 优先写工具类：`secret-scan`、`sast`、`semantic-search`、`dependency-scan`、`modernization`、`context-pack`。
> `high` / `release` 任务至少运行 `.agents/scripts/tooling-router.py --mode plan`，或在 `progress.md` 记录无法运行的原因。
> `release` 任务若 `secret-scan`、`dependency-scan` 或匹配 `block` 工具 disabled / missing / skipped，必须写入 `progress.md` 的 `Verification Waivers` 或 Tooling gaps。
> 证据可以是命令、exit code、`.agent-state/runs/<run_id>/...` artifact、截图路径、trace/report、接口响应摘要或人工 QA 记录；旧 `.agents/runs/<run_id>/...` 只做兼容读取。
> “已测试”“看起来正常”等没有命令、artifact、截图、trace、API 响应或人工 QA 记录的表达不算证据；没有证据的必需验证不能标记为完成。
> `optional` 或明确 `not-needed` 的检查不需要长篇 waiver；必需验证失败、超时、不可运行或被替代时，必须写入 `progress.md` 的 `Verification Waivers`。
> `high` / `release` 的代码行为变化，或核心逻辑、跨层、权限 / 认证、字段契约、数据迁移、回归问题必须完成完整 Test Evidence Gate；普通 focused bugfix 可只记录修复前复现和修复后回归证据。项目无测试基础时写 waiver，不强行制造脆弱测试。
> 先写测试时不要只写一组 happy path；按风险选择 `case_class`。核心行为、权限 / 认证、字段契约、数据迁移、release 或回归任务至少覆盖正常路径和一个主要风险类别（负向、边界、权限拒绝、兼容性、失败路径、property 或 contract），否则写 waiver / not-needed reason。
> Structural Index / Graphify / CodeGraph 只作为派生结构证据；`query-existing` 可读取只读 CodeGraph 查询结果或已有 fresh/legacy `GRAPH_REPORT.md`。Graphify 的 `refresh-and-query` 必须用户显式授权且主要用于 report/non-code/legacy 场景；CodeGraph 默认只允许只读查询，建索引 / watch 只能作为项目级显式试点 `trial-index-codegraph`，且不得由 tooling-router run 或 hooks 自动触发。

## Acceptance Evidence Map
| acceptance item | scenario_id | case_class | evidence method | evidence location | status |
|---|---|---|---|---|---|
| 验收项 1 | not-needed / S1 / 待填写 | positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract / not-needed | command / artifact / screenshot / trace / API response / manual note | 待填写 | pending / pass / fail / waived |

## Test Strategy
### Test-first decision
| item | value |
|---|---|
| Decision | red-green / characterization-before-code / pre-fix-reproduction / post-change-only-with-waiver / not-testable / not-needed |
| Applies to | new feature / bugfix / regression / core logic / permission / data migration / UI / docs / 待填写 |
| Reason | 待填写 |
| Pre-code evidence | failing test / characterization test / reproduction command / not-needed / waiver |
| Anti-overfit guard | positive-plus-risk-case / parameterized examples / property-or-invariant / contract verification / golden-reviewed / waiver / not-needed |
| Red evidence command | failing test / reproduction command / characterization command / not-needed / waiver |
| Expected failing assertion | behavior missing / regression reproduced / invariant violated / not-needed / waiver |
| Post-fix evidence command | same test / focused regression / behavior smoke / not-needed / waiver |
| Same scenario_id | S1 / not-needed / waiver |

> 完整 red-green 字段只在选择 red-green、回归 / 高风险缺陷、核心 / 跨层 / 权限 / 字段 / 迁移改动，或普通 bugfix 缺少明确 pre/post evidence 时需要。普通 focused bugfix 可用修复前复现 + 修复后回归证据收口，不因 bugfix 身份强制填写完整表。

| layer | required? | command / evidence | result / waiver |
|---|---|---|---|
| Test Evidence Gate | yes / no | reproduce / behavior test / API smoke / browser evidence / waiver | pending |
| focused unit / service test | yes / no | 待填写 | pending |
| build / typecheck / lint | yes / no | 待填写 | pending |
| API smoke / integration check | yes / no | 待填写 | pending |
| browser / UI regression | yes / no | 待填写 | pending |
| data / migration verification | yes / no | 待填写 | pending |
| deployment / rollback check | yes / no | 待填写 | pending |

> 不要求每层都跑；只要求解释为什么需要或不需要。必需层不可运行时，必须同步到 `progress.md` 的 `Verification Waivers`。
> bugfix 优先先有修复前复现证据；核心逻辑优先行为测试或公共接口测试；跨层改动至少有端到端路径证据。
> TDD 是可选策略，不是全局 gate；但如果选择 test-first，red 阶段必须说明失败原因是目标行为缺失，而不是 fixture / 编译 / mock 配置错误。高风险逻辑可考虑 property / invariant、契约测试或参数化样例；mutation testing 只作为核心模块抽检，不默认阻断。

## Defect Closure Criteria
> 仅在 bugfix、回归、测试失败、生产问题或用户可复现异常时填写；非缺陷任务可写 `not-needed`。

| defect_id | reproduce evidence before fix | close condition | regression check | owner | status |
|---|---|---|---|---|---|
| not-needed / DEF-YYYYMMDD-01 | failing command / UI steps / API response / screenshot / no-repro waiver | 待填写 | command / artifact / manual note | 待填写 | pending / verified / waived |

> 修复缺陷时，必须能从 `findings.md` 的 `Defect Records` 追溯到这里的关闭条件；没有修复前复现证据或修复后回归证据时，只能写 `waived`，不能写 `verified`。

## Execution Table
| slice_id | slice_type | files | action | input | output | acceptance | verify | evidence | independent_checkpoint | parallel_safe | done |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SL1 / 待填写 | story / risk / technical / release / docs / not-needed | `待填写` | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | yes / no / not-needed | yes / no / conflict-risk / not-needed | 待填写 |

> Drift rule：如果实际文件集合、动作或验证方式与表格不一致，先更新本表，再继续执行。
> Micro-Spec rule：每一行都是一个可独立验证的 slice；优先机器验证，不可机器验证时写明人工 QA 或 waiver。`story` slice 对齐用户价值，`risk` slice 对齐负向 / 安全 / 回归风险，`technical` slice 对齐支撑性重构或工具治理；`parallel_safe=no/conflict-risk` 时不要并行交给多个 agent。

## Plan / Checklist Hygiene
> 长计划、代码块密集计划或 checkbox 计划必须说明它是 active state 还是 reference-only scaffold。未维护的 checkbox 不能作为完成状态依据。

| item | value |
|---|---|
| Plan length / shape | compact / normal / long-code-heavy / not-needed |
| Checkbox tracking | active-maintained / scaffold-reference-only / not-used |
| Reference-only marker needed | yes / no / not-needed |
| Current active state source | task_plan / progress / findings / latest-user-instruction / not-needed |
| Notes | 待填写 |

## Acceptance criteria
- [ ] 验收项 1
- [ ] 验收项 2

## Evidence required before done
- [ ] 每个验收项都有对应验证记录
- [ ] 每个验收项都有 `Acceptance Evidence Map` 证据
- [ ] 触发 Behavior / Example Contract / high / release：验收项已映射到 `Behavior Scenarios` 的 `scenario_id`，或明确 `not-needed`
- [ ] 复杂任务 / release：`progress.md` 的 `Final Evidence Ledger` 已把 Matrix、补充脚本、人工 QA 和 waiver 合成最终验收口径
- [ ] 每个 `Execution Table` 行都有 `verify` 结果
- [ ] 每个必需验证都有 `evidence`
- [ ] 用于交付证据的临时脚本已复制到 `.agent-state/runs/<run_id>/scripts/`，并记录 command、sha256 和输出 artifact；不适用时写 `not-needed`
- [ ] 实际 diff 没有违反 `Negative Constraints`；如有偏离，已更新计划并说明原因
- [ ] bugfix / 回归 / 生产问题：修复前复现证据和修复后回归证据已对应 `findings.md` 的 `Defect Records`
- [ ] 写代码或扩大范围前已完成 Read-Before-Decide
- [ ] 如果任务从只读 / 验收 / 排障转为代码修复，已重查 Requirement Contract、Risk Tier、Architecture Impact 和 Test Strategy
- [ ] 如果产品结果、范围或重要取舍发生变化，已记录 Options、Decision、Trade-offs、验证变化和是否需要用户确认
- [ ] 如果触发高风险 Grill Check，已记录关键歧义、领域词汇 / 历史决策冲突、负向约束和用户确认状态
- [ ] 如果触发 Test Evidence Gate，已记录修复前复现、行为测试、API smoke、浏览器回归或 waiver
- [ ] `high` / `release`、核心行为、权限 / 认证、字段契约、数据迁移或回归：关键 `case_class` 已覆盖正常路径和至少一个主要风险类别，或有明确 waiver / not-needed reason
- [ ] 未验证内容已写入 `progress.md` 的未验证部分
- [ ] `high` / `release`：`tooling-router` 的 plan/run/skip reason 已写入 `progress.md`
- [ ] `high` / `release`：dirty classifier 或等效分类结果已写入 `progress.md`
- [ ] `high` / `release`：`Changed Files Manifest` 已写入 `progress.md`
- [ ] `high` / `release`：Red-team checklist 结论已写入 `progress.md`
- [ ] `release / external-system`：本地 S0/S1 Release Red-team 已完成，或有明确 waiver
- [ ] `release / external-system` 且构建 jar / dist / container / 部署包：`Release Artifact Source Gate` 已记录 `clean-source-build / source-manifest-build / allowed-diff-build`，或有用户显式风险接受
- [ ] commit / push：staged/tracked diff 中无未解释 `.env*`、runtime data、dump、HAR、trace 或大文件
- [ ] 必需验证失败、超时或被替代时：`Verification Waivers` 已写入 `progress.md`
- [ ] `release` 级 UI / 浏览器改动：`Browser / UI Evidence` 已写入 `progress.md`，或已写明跳过原因
- [ ] `Architecture Impact: yes`：已更新 `architecture-notes.md`，或已写明不更新理由

## Risks
- 风险 1：待填写
- 风险 2：待填写

## Open questions
- 问题 1：待填写
- 问题 2：待填写
