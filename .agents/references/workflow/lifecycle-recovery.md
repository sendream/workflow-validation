# Workflow Module: lifecycle-recovery

Runtime authority: detailed reference only; project `AGENTS.md` remains routing authority.
Default loading: no; read only when the matching gate or task phase is active.
State boundary: no task state, runner authority, or delivery approval.

## Defect Management
缺陷管理是三文件内的轻量闭环，不是独立 tracker。

触发条件：
- 修复 bug、回归、测试失败、生产问题或用户可复现异常。
- `Verification Matrix` 中有必需验证失败、超时、flaky 或被 waiver 替代。
- 需要跨会话继续定位，或已有失败路径可能被下一会话重复尝试。

记录位置：
- `findings.md` 的 `Defect Records` 记录复现、期望/实际、环境、严重度、优先级、影响范围、根因、修复策略、回归证据和状态。
- `task_plan.md` 的 `Defect Closure Criteria` 记录关闭条件。
- `progress.md` 的 `Defect Status` 记录状态、owner、验证证据和是否允许交付。

规则：
- 修复前必须先有复现证据：失败测试、失败命令、接口返回、浏览器步骤、截图/trace 或人工可复现记录。
- 先建立最小可复现反馈环，再提出假设、修复和回归；没有反馈环时不得把猜测修复写成 verified。
- 无法复现时写明 `no-repro`、替代验证和 owner；不得把猜测修复标记为 `verified`。
- 修复后必须有回归证据，且能对应修复前的复现路径。
- 状态只用：`open -> triaged -> fixing -> fixed -> verified -> closed`；无法稳定复现写 `no-repro`，验证豁免写 `waived`，不适用写 `not-needed`。
## Failed / Rejected Paths
只保留可能被后续会话再次误走的高价值失败结论，不维护 strike、retry counter、loop mode 或专用 validator。

- 在 `findings.md#Errors / Failed Attempts` 记录 attempted path、observed result、reason rejected / likely cause、next different strategy 和必要 evidence reference。
- 长日志与原始输出留在 `.agent-state/runs/<run_id>/`；三文件只保存结论与精确指针。
- 命中已记录的失败路径时直接换用不同策略；若确需重试，先说明出现了什么新证据。
- 同族缺陷再次出现时可做一次 targeted sibling search，再选择 local fix 或 scoped pattern fix；不得借此静默扩大范围。
- release/full regression 暴露旁支漂移时，分类为 blocker、waiver with alternative evidence 或 follow-up。
## Known-Bad Path Guard
已验证的失败路径不能只在本轮起作用。环境、构建、测试、部署、SSH、浏览器或外部命令任务开始前，必须先检查 `.agents/references/project-conventions.md` 和 `.agents/references/common-pitfalls.md` 是否已有相同场景的坏路径和稳定路径。

规则：
- 如果匹配到已知坏路径，默认从记录的稳定路径开始。
- 如果本轮必须重试坏路径，先写明 Intent Declaration：例如验证环境已修复、排除新变量、用户明确要求，或本轮目标就是修环境。
- release / deploy / 生产交付语境命中已知坏路径且已有稳定替代方案时，默认 hard block；除非用户明确要求验证或修复该坏路径，或稳定替代方案失效。
- 如果坏路径再次失败，不继续累计盲试；把 evidence 写入 `findings.md` 的 `Errors / Failed Attempts`。
- 稳定经验直接写入 `common-pitfalls.md` / `project-conventions.md`。Knowledge Promotion 表只在本轮真的要 promote 时才填，不作为默认收口仪式。
## Environment Debt Gate
环境债务是已知坏环境暂未统一修复，但已有稳定替代方案可支撑生产开发或发布交付的状态。

规则：
- 已知坏环境 + 稳定替代方案存在：当前交付必须默认走稳定替代方案；不要在生产开发 / 发布交付阶段顺手尝试修环境或默认重试坏路径。
- 已知坏环境 + 没有稳定替代方案：环境问题升级为当前 blocker，可以进入排障 / 修复环境流程。
- 未知失败：先诊断到可命名的失败模式，再决定提升为 Known-Bad Path、记录环境债务、修复根因或作为当前 blocker。
- 只有用户明确要求修环境、本轮目标就是环境修复、需要验证坏路径已修复，或稳定替代方案失效时，才重新尝试坏路径；尝试前写明 Intent Declaration、边界和回退点。

记录字段：
- Bad environment / path：具体坏环境、命令入口或路径。
- Stable workaround：当前已验证稳定替代方案。
- Production policy：生产开发 / 发布交付阶段默认怎么走。
- Repair trigger：何时才允许修复或重新验证坏环境。
- Owner / refresh when：谁后续处理，什么环境变化时复查。
- Status：open / deferred / fixing / verified / closed。
## Dirty Worktree Classifier
push 前的脏工作区判断优先用结构化分类，避免只看 `git status` 长列表。

- 推荐入口：`.agents/scripts/classify-worktree-dirty.py --format json`。
- 准备 commit / push 时优先补 staged 视角：`.agents/scripts/classify-worktree-dirty.py --staged-only --format json`。
- 分类至少区分：`sensitive`、`generated`、`workflow-state`、`source-or-doc`、`large`。
- `high` / `release` 任务要把摘要写入 `progress.md` 的 `Changed Files Manifest` 或 Push Gate Evidence。
- 出现 `.env`、私钥、token、数据库文件、缓存、部署包、日志、大文件或无关生成物时，默认不 push；除非已从 staged diff 排除并记录原因。
- staged/tracked diff 中出现 `.env*`、Redis / DB / Weaviate / Milvus / Elasticsearch / SQLite runtime data、dump、HAR、trace 或运行时大文件时，默认 S0 Push Blocker；只有明确是 `.env.example`、fixture、schema/migration 且有 waiver、回退点和核对证据时才可继续。
- 脚本只是辅助证据；最终仍以 staged diff、用户授权和项目规则为准。
## Push / Commit / Delivery Cleanup
Push Gate 的顶层授权和阻断原则在 `AGENTS.md`；本节只承接执行细节，不能放宽 overlay、sensitive、runtime data 或外部写入边界。

提交 / 推送前：
- 先运行或等效执行 `.agents/scripts/validate-workflow-overlay-boundary.py --staged-only --require-local-exclude`；workflow overlay staged、staged deletion 或本地 overlay 被误删时默认阻断。
- 运行或等效执行 `.agents/scripts/classify-worktree-dirty.py --format json`；准备提交时优先补 `.agents/scripts/classify-worktree-dirty.py --staged-only --format json` 检查 staged diff。
- 大脏工作区默认先用 `.agents/scripts/classify-worktree-dirty.py --summary` 或 JSON `context_summary` 作为低噪声视图；完整 `git status --short` 只作为 artifact 或排障输入，不直接塞进上下文。
- 一个 commit 默认只对应一个任务目标；业务代码、workflow overlay、生成物 / 证据 / 文档应分开提交，除非它们是同一验收项的不可分割证据，并在提交前说明原因。
- `standard` 记录轻量 Push review；`high` / `release` 有三文件写授权时把 dirty summary、blocking verification、waiver 和 Red-team 结论写入 `progress.md`，只读审查无写授权时写入最终回复或指定 report artifact。
- `Risk Tier=release` 或 `Impact Scope=external-system` 必须执行本地 S0/S1 Release Red-team；不强制外部模型 reviewer，内部 Codex 只读 reviewer 仍按 Policy-Auto assessment / preferred 规则处理。
- `release` 任务如 `secret-scan`、`dependency-scan` 或匹配的 `block` 工具 disabled / missing / skipped，必须写入 `Verification Waivers` 或 Tooling gaps，不能只写“非阻断”。
- 检查敏感文件、密钥、日志、截图、HAR、trace、大文件、无关生成物和 runtime data 是否混入。staged/tracked diff 中出现 `.env*`、私钥/token、Redis / DB / Weaviate / Milvus / Elasticsearch / SQLite runtime data、dump、HAR、trace 或运行时大文件时，默认 S0 push blocker；只有明确是 `.env.example`、fixture、schema/migration，或用户接受 waiver 且有回退/核对证据时才能继续。
- 存在 blocking 验证失败、未解释敏感风险、runtime data 风险或无关文件混入时，不得 push，除非用户明确接受风险。

commit / push 成功后：
- 提交或推送后的真实状态以 Git HEAD、index、upstream 和交付结果为准；更新面向用户的简短 handoff 即可，不再用三文件 lifecycle 或专用措辞镜像 Git 状态。
- 复杂任务正式关闭或切换 active task 前，归档到 `.agents/tasks/<task-id>/`，或写入 `.agent-state/tasks/archive-ready/<task-id>/` / 明确 `archive-deferred` 原因。
## Release Red-team Review
`release` 或 `external-system` 任务不能只按普通 local checklist 收口。

- 必须执行本地 S0/S1 Release Red-team；这不替代 Policy-Auto reviewer assessment。
- 内部 Codex 只读 reviewer 若 assessment=`preferred`、`Authorization scope=policy-auto` 且 Capability Fact Rule 全部满足，必须启动；pre-start 未启动只能记录 `tool-unavailable / runtime-policy-blocked / explicit-delegation-required / packet-invalid / brief-invalid / validator-failed / explicit-denied` 和 fallback；已启动后未完成记录 `review-incomplete / reviewer-timeout / budget-exceeded` 和 fallback。
- 外部模型 reviewer（Gemini / Claude / 第三方 CLI/API）不强制，且必须有 `external-standing-opt-in`、任务授权或会话授权；写入型 agent、deploy / DB write / push / external-write、secrets 访问仍需用户明确授权。
- S0/S1 检查至少覆盖：权限 / 认证反向验证、生产配置误改、数据库 / 缓存 / 队列回退点、tracked `.env` / runtime data、Release Artifact Source Gate、blocking verification、rollback point。
- 发现 S0 必须阻断交付；S1 原则上阻断，除非有明确 waiver、owner 和后续动作。
## Task Closeout Gate
`high` / `release` / `Impact Scope=external-system` 收口时使用 fail-closed 总闸，防止 agent 选择性漏跑证据、reviewer 或 manifest 检查。

- 入口：`.agents/scripts/validate-task-closeout.py --root <project> --task-plan task_plan.md --progress progress.md --findings findings.md --require-existing-artifacts --format json`。
- 它只编排现有 deterministic validators，不创建 runner、不启动 reviewer、不写三文件、不新增第二状态源。
- 默认检查 active task id 一致性、traceability、Workflow Trace consistency、Final Evidence Ledger / waiver、typed evidence refs、Source Roots / Repos Touched、reviewer assessment、review authorization 和 Next Action quality。Knowledge Promotion 与 docs fact drift 有独立入口，不由 closeout 再编排一遍。
- 最终回复前必须有 G21 closeout decision。普通 standard 可用 `task_closeout=focused` 和 focused evidence 摘要；`high` / `release` / `external-system` 或显式 closeout gate 使用 fail-closed bundle。
- `progress.md#Current Status` 应记录任务自身的 `Lifecycle state`：`planned / in_progress / verifying / ready_to_submit / submitted / archived / blocked / deferred / cancelled`。`task_closeout=strict-pass` 后不能继续把根三文件标成 `active / in_progress`；该字段只描述任务 handoff / archive 状态，不作为 commit、push 或 upstream 状态的代理。
- 如果证据字段引用了 `.agent-state/runs/<run_id>/...`，必须用 `validate-run-manifest.py --strict-current` 检查对应 run manifest；证据字段包括 `Verification Matrix.evidence`、`Workflow Trace.evidence`、`Validation.evidence/artifact`、`Run Evidence.run_id/manifest/artifact/notes`、`Final Evidence Ledger.supplemental_evidence/artifact` 和 `Role Review Summary.packet`。`required_checks`、`unresolved_risk`、需求说明、负向样例或测试描述中的示例路径不应被当成真实 run evidence。
- 如果 `Active Task Snapshot` / `Traceability` / `Current Status` / `Delivery Metadata` 等状态字段声明了当前具体 `Run ID`，或 `progress.md#Run Evidence` 填写了具体 `run_id`，对应顶层 `.agent-state/runs/<run_id>/manifest.json` 必须存在；`optional / 待填写`、表头、`Trace ID` 或子目录 manifest 不能替代 active run 顶层 manifest。
- `commit-ref`、`push-ref`、`source-file:<root_id>:<path>`、`artifact:`、`release-source:` 是证据引用，不是 run id；不得写入 `Run Evidence.run_id` 来绕过 run manifest。命令型 `PASS` 仍必须引用 `.agent-state/runs/<run_id>/manifest.json` 或 run-local durable artifact。
- 如果项目根不是 git worktree、任务跨多个 source root、release/external-system 涉及子仓 / 产物源，或实际使用 Structural Index / CodeGraph，strict closeout 必须填写 `progress.md#Source Roots / Repos Touched`，用于确认实际 source root 身份和证据归属；Git cleanliness 与 upstream 状态只在实际 commit / push / delivery 边界直接检查。
- 不用三文件中的措辞推断 commit/push 是否发生；需要交付事实时直接读取 Git 或远端状态。M01/M13 的授权、secret/runtime-data 和目标分支边界继续独立生效。
- 如果本轮实现了 docs / tests / README 中原先写成 future work、not implemented、planned、TODO、missing 或 disabled 的能力，必须在 `progress.md#Docs Fact Drift Check` 记录明确短语、项目根内扫描路径和处置；用 `validate-doc-fact-drift.py` 检查。扫描路径不得使用 `..` 跳出项目根，不得使用 `.` / `**/*.md` 这类 repo-wide glob，也不得指向 `.agent-state`、`.agents/tasks`、Graphify / CodeGraph 输出，或 `node_modules`、`dist`、`build`、`coverage`、`.next`、`target`、缓存、日志等生成/运行/归档目录；`accepted-stale` / `deferred` 必须有证据或理由。
- 如果 `release` / `external-system` 同时存在 jar / container / deploy package / release bundle / zipped dist artifact 等发布产物信号，必须把 Release Artifact Source Gate 纳入 closeout；普通 evidence artifact 或 docs drift 里的 `dist` / `build` / `coverage` 目录示例不算发布产物。
- Completed task archive hygiene 只在显式 `--archive` 或 `--require-archive` 时检查；旧 archive 用 legacy warn，不让历史包袱阻断当前 active task。新 archive summary 的 `Summary / Evidence Index / Boundaries` 不能只写占位符；`evidence_manifests` 只能列 `.agent-state/runs/<run_id>/manifest.json`，业务报告 JSON、子目录 manifest 或裸 run 目录只能作为 Evidence Index/artifact 说明。
- `fast path / low` 不默认使用 closeout bundle；focused verification 足够时不加载 full gate。
