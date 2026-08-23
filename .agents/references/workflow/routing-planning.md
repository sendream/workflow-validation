# Workflow Module: routing-planning

Runtime authority: detailed reference only; project `AGENTS.md` remains routing authority.
Default loading: no; read only when the matching gate or task phase is active.
State boundary: no task state, runner authority, or delivery approval.

## Gate Registry / Routing Notes
项目根 `AGENTS.md` 是 gate ID、顶层路由和冲突裁决来源。本文件只展开已触发 gate 的执行细节和非扩权示例；skills、templates 和 code review guide 只能引用这些 gate，不得放宽、扩大或另建触发条件。

Fast / complex orientation is owned directly by `AGENTS.md`; it has no routing Gate or wrapper Skill.

- `G00_REVIEW_AUTH`：Review / Audit Read-Only Boundary。
- `G03_CLARIFICATION`：Clarification First。
- `G04_SCOPE_BRAKE`：Scope Soft Brake。
- `G06_ACTIVE_MIGRATION`：Active Task Migration Check。
- `G09_BEHAVIOR_CONTRACT`：Behavior / Example Contract。
- `G10_TEST_EVIDENCE`：Test Evidence Gate。
- `G14_STRUCTURAL_INDEX`：Structural Index Decision。
- `G16_ROLE_REVIEWER`：Multi-Agent Role Assessment / Policy-Auto Role Reviewer。
- `G17_SHIP_CHECK`、`G18_RELEASE_SOURCE`、`G19_CODE_REVIEW`、`G20_PUSH_OVERLAY`、`G21_TASK_CLOSEOUT`：交付、发布、代码审查、push overlay 和收口 gate。
## Template Scaling
三文件是复杂任务心智模型，不是所有字段都必须写满。

- `low` 或边界清晰的 `standard` 任务：只填写目标、风险、范围、负向约束、最小验证、当前状态和必要证据；无关字段写 `not-needed`。
- `high` / `release` 任务：保留 Requirement Contract、Negative Constraints、Verification Matrix、Execution Table、Changed Files Manifest、waiver、handoff 和 review 证据。
- fast path 不强制启用三文件；任务中途风险扩大时，再升级为复杂任务并补齐最小必要字段。
- `review-only / plan-only` 是 pre-routing 只读模式；即使需要复杂分析，也只输出报告，不创建、归档或修改三文件，除非用户明确授权写入。
## Minimal Viable Design
- 先回答“满足当前需求的最小稳定改动是什么”，再考虑标准化改造。
- 不新增当前需求用不到的抽象、配置、兼容层、fallback 或 just-in-case 逻辑。
- 每个被修改文件都应能追溯到 `Requirement Contract`、`Execution Table` 或明确的修复清理。
- 无关顺手优化只记录建议，不直接改。
## Clarification First
当 G03 已选择时执行。Trigger 以 Gate Card 为准。这不是 high/release 专用 Grill Check。

执行规则：
- 仓库、官方来源或当前三文件能查清的事实不要问用户；先查再问。
- 只问当前决策前沿：答案会改变产品行为、验收、范围或权限，且其前置选择已经落地。不要提前问还依赖未决选择的问题。走完决策树、问到没有剩余假设，都不是完成条件。
- 必须先看到东西才能答的问题，停止追问，改做有界试探或一次性原型；不要用更多问题假装已经决定。
- 先问 1 到 3 个真正阻断的问题；fast path / low 最多问 1 个，非阻断问题做保守假设。
- 每个问题必须给 2 到 4 个互斥选项，推荐项放第一并标注“推荐”，并说明取舍。
- 不能用开放式问题替代可枚举选项；无法枚举时说明原因。
- Clarification Coverage 至少检查：`goal`、`output`、`non-goals`、`acceptance`、`data-permission`、`validation`、`scope`；不相关项写 `not-needed`，不要为了填表追问无关问题。
- Answer landing：用户选择或采用的默认项必须进入 `requirement-contract`、`assumptions`、`scope-control`、`negative-constraints`、`behavior-scenarios`、`verification-matrix` 或 `not-needed` 中的一个明确落点；未落地的回答不算已吸收。
- `high` / `release` 中的关键歧义如果仍未确认，必须进入 Grill Check、waiver 或 blocker，不得静默假设。
## Scope Soft Brake
当 G04 已选择时执行。Trigger 以 Gate Card 为准。这是暂停确认点，不是硬性的文件数量 gate。

机械模板同步、批量 rename、格式化、只改 docs/tests 且无行为变化时，按 Card 的 retire/downgrade 处理，不要把 G04 当成已命中。release packaging 清单仍进 Dirty Worktree Summary。

执行规则：
- 先写清 `modifiable files / protected files / expected file count / module count / pause trigger`。
- 增加 Scope Hammer：把需求拆成 `must-have`、`nice-to-have`、`out-of-bounds`，并说明哪些内容可以延期、不做或必须先用户确认。
- 如果继续一轮完成，说明原因、拆分为何更差、验证如何覆盖。
- 如果拆分，先把剩余 slice 留在 `Execution Table` 或 `Next Action`，不要顺手扩大实现。
- 用户已明确授权大范围标准化或同步时，可标记 `user-approved-wide-scope`，但仍需 Diff-to-Plan 和 evidence。
## Active Slice / Rollover
Active Slice / Rollover 是长任务、跨 phase 或 handoff 的轻量状态压缩，不是新计划、runner 或第二状态源。

触发条件：
- 当前任务已经跨多个实现 / 验证 slice，或 `progress.md` 开始堆积历史流水。
- 准备从 planning / implementation / validation / closeout 切换到下一阶段。
- 需要交给下一会话，或 closeout 前发现还有未完成 slice。
- Scope Soft Brake 触发后决定拆分，而不是继续扩大当前修改。

执行规则：
- `task_plan.md#Execution Table` 仍是 slice 计划来源；`progress.md#Current Status` 只记录当前 `Active slice id`、`Rollover state` 和 `Rollover target`。
- `rollover_state=split-needed / handoff-ready / carried-forward / blocked` 时，不得同时把 `task_closeout` 写成无条件 `strict-pass` 或把 lifecycle 写成 `archived`。
- 每次 rollover 必须有单一可执行 `Next Action`、必要证据 manifest、open waiver / blocker 摘要和禁止动作边界。
- 旧 slice 的详细日志、长 stdout、reviewer 原始输出和 run artifacts 留在 `.agent-state/runs/<run_id>/`；三文件只保留摘要和路径。
## Active Task Migration Check
当 G06 已选择时执行。Trigger 以 Gate Card 为准。它处理“业务项目已经同步了新版 workflow，但当前 active 三文件仍是旧 gate 结构”的场景，不是新状态源，也不是所有任务的默认步骤。

检查内容：
- `task_plan.md` 的当前阶段、Non-goals、Negative Constraints、Phase Change 记录是否仍匹配实际执行阶段。
- `high` / `release` 是否已补 `Behavior Scenarios` 或明确 `not-needed`，并把 `Verification Matrix`、`Acceptance Evidence Map`、`Final Evidence Ledger` 用 `scenario_id` 串起来。
- `progress.md` 是否已有 `Final Evidence Ledger`，而不是只散落在 `Run Evidence`。
- `progress.md` 是否用规范值记录 `Isolated Reviewer` assessment：`Trigger decision = not-needed / assessment-only / preferred`；pre-start 未启动结果写 `Start required=no` + typed non-start `Start result`，启动或启动后未完成结果写 `Start required=yes` + typed started / incomplete `Start result`。
- 旧 read-only / no-code / health-check scaffold 约束是否仍残留在 active plan 中；如果实际已进入实现或测试，必须执行 Phase Change 回填。
- `task_plan.md`、`progress.md`、`findings.md` 的 active task id 是否一致；不一致时不得继续 coding、deploy 或 ship-check。

执行方式：
- 首选运行：`.agents/scripts/validate-active-task-migration.py --root <project> --task-plan task_plan.md --progress progress.md --findings findings.md --format json`。
- 该脚本聚合 traceability、evidence/waiver、reviewer assessment 三类 strict validator，并额外检查 read-only/no-code 约束与实现进度的 phase drift。
- 它只检查当前 active 三文件；不扫描 `.agents/tasks/` 冷归档，也不要求修复历史任务。

收口规则：
- 检查失败时，不继续把 high/release 任务写成 `completed` 或无条件 ship；先迁移三文件或记录明确 waiver。
- 迁移不是重写历史流水账；只补当前阶段需要的最小证据链、Phase Change、Final Evidence Ledger 和 assessment。
- 如果只是同步 workflow 且无 active high/release 任务，记录 `not-needed` 即可，不增加 fast path 成本。
## Behavior / Example Contract
当 G09 已选择时执行。Trigger 以 Gate Card 为准。这是需求到验证的轻量行为锚点，不是默认 BDD，也不是 high/release 自动税。

无行为变化的文档、格式化、overlay、packaging 或普通 focused bugfix 不应进入本节；用验收项 + focused verification，或写 `not-needed`。API / 字段 / 权限 / 外部系统契约变化时补 `Interface / Domain Contract Delta`。

执行边界：
- 默认只在 `task_plan.md` 写 Markdown 表，不生成 Cucumber / Gherkin `.feature` 文件。
- 不引入 GitHub Spec Kit `.specify`、第二套 specs/tasks、第二套 progress 或第二套 evidence ledger。
- `then / observable outcome` 必须是外部可观察结果：API response、UI state、permission denial、error code、artifact、audit log 或人工可复验现象。
- 规则密集或字段空值类需求用 `Example Table`；跨接口 / 字段 / 权限 / 外部系统变化用 `Interface / Domain Contract Delta`。
- `Behavior Scenarios`、`Example Table`、`Verification Matrix`、`Acceptance Evidence Map` 和 `Final Evidence Ledger` 通过 `scenario_id` 与 `case_class` 串起来；不要新增独立 `Scenario Evidence Ledger` 或 `test_matrix.md`。
- `case_class / case_type` 只表达当前例子或证据覆盖的风险类别：`positive / negative / boundary / regression / compatibility / permission-deny / failure-path / property / contract`。`not-needed` 是适用性哨兵值，不是风险类别；仅用于非行为类验收或明确不适用行。它不是测试任务列表。
- 先写测试时不要只写一组 happy path；核心行为、权限 / 认证、字段契约、数据迁移、release 或回归任务至少覆盖正常路径和一个主要风险类别，或写明 waiver / not-needed reason。
- 测试 oracle 必须尽量独立于实现：expected outcome 来自 `Requirement Contract`、用户回答、现有已确认行为、接口 / schema 契约、独立 fixture、人工领域确认或 waiver；不要用被测实现的同构逻辑计算 expected，也不要把未经审阅的 snapshot / golden 当前输出当成需求真值。
- 复杂 / high / release 行为任务收口前必须做需求对账：测试通过只能证明测试 oracle 被满足，不能单独证明需求被正确理解；若 `Requirement Reconciliation` 发现 `mismatch` 或 `needs-human-check`，相关验收不得无条件 `PASS`。
- high / release 的行为变化至少要有一个 linked scenario，或明确说明 `not-needed` 的原因。
- 结构校验入口：`.agents/scripts/validate-traceability.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger`。它只检查 acceptance / scenario / evidence / waiver 链路，不判断业务语义；原始 `.agents/templates/` 默认跳过，只有显式 `--check-template` 才检查模板占位。
## Phase / Scope Recheck
阶段或范围变化时做一次直接复查，不创建新的 Gate、Skill 状态或强制 spec。

触发条件：
- 从只读理解、验收测试、问题定位转为代码行为变更、API / 数据流变更、部署修复或生产操作。
- 实际影响范围从 `visible / file-linked` 扩大到 `cross-package / external-system`。
- 验证矩阵新增必须项、原必需验证失败并需要替代方案，或缺陷从 `no-repro` 转为可复现。

执行要求：
- 重读 `task_plan.md` 的 Goal、Requirement Contract、Negative Constraints、Verification Matrix 和当前 Execution Table 行。
- 重查 Requirement Contract、Risk Tier、Architecture Impact、Test Strategy 和 Sensitive Operations。
- 若产品结果或重要取舍变化，在 `Decision Notes` 或 `progress.md` 中用 5 行以内记录 Options、Decision、Trade-offs、验证变化和是否需要用户确认。
- 不要求为明确小修复写完整 spec；目标是阻止“验收中顺手改代码”绕过设计和验证。
