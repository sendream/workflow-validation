# Workflow Module: reviewer-governance

Runtime authority: detailed reference only; project `AGENTS.md` remains routing authority.
Default loading: no; read only when the matching gate or task phase is active.
State boundary: no task state, runner authority, or delivery approval.

## Review-to-Implementation Authorization Gate
当 G00 已选择时执行。Trigger 以 Gate Card 为准。Review / audit / 评估 / 核查 / 审查 / 复盘类任务默认是只读任务。该 gate 用来防止“审查发现问题”被误读成“可以直接修代码”。

规则：
- 业务项目路径只授权读取核查，不授权写入该项目。
- `accepted` finding 只表示主 Codex 认可该问题存在；它不是 implementation authorization。
- S0 / S1 只提高修复紧迫性，不绕过用户授权、写入范围、Push Gate 或 Sensitive Operations。
- 转入实现前必须明确：目标 repo/path、允许写入范围、禁止动作、是否允许测试 / 构建 / 部署、是否允许 commit / push。
- `high` / `release`、业务项目写入、生产 / 外部系统、多个 reviewer finding 或长会话时，在 `progress.md` 记录 `Review / Audit Boundary`。

记录口径：
- `Mode=review-only / plan-only` 时，只能读、分析、在回复中写报告或草案计划；不得修改 `task_plan.md` / `progress.md` / `findings.md`，不得写业务源码或执行交付动作。
- `Mode=report-write-only` 时，只能写用户指定的单个报告 artifact；必须记录 `Write authorization=report-only`、`Authorization source`、`Allowed write scope`、`Finding disposition policy=accepted-as-finding-only` 和 `Transition decision=report-write-only`；不得写三文件、业务源码或执行交付动作。
- `Mode=implementation-authorized` 时，必须同时记录 `Write authorization=task/session`、`Authorization source`、`Allowed write scope`、`Finding disposition policy=implementation-approved` 和 `Transition decision=implement-authorized`。
- 可用 `.agents/scripts/validate-review-authorization.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger --format json` 检查 review/audit 任务是否在无授权情况下出现实现证据。
## Role Reviewer / Policy-Auto Review
本节是 `AGENTS.md#G16_ROLE_REVIEWER` 触发后的执行语义权威；顶层触发、gate id 和冲突裁决仍以项目根 `AGENTS.md` 为准。`isolated reviewer` 是 legacy compatibility alias，新文本应优先使用 `Role Reviewer`。

Role Reviewer 是 `enhanced-review` 的条件增强项，不是默认 gate、主流程或第二事实源。

`Multi-Agent Role Assessment` 是 isolated reviewer 的角色化评估口径，不是新的 workflow、编队机制或实现授权。主 Codex 仍负责上下文、计划、实现、证据维护和最终裁决；子 agent / 外部 reviewer 只做只读 challenge。

Capability Fact Rule：
- `reviewer_count`、`campaign_count` 和 `implementation_worker_count` 的默认值都是 `0`。
- `assessment required` 只表示必须记录是否需要 reviewer；它不是启动许可，也不等于已启动。
- `preferred` 只是 trigger decision；只有同时具备 start authority、runtime tool capability、runtime policy permission、valid Agent Brief、valid Reviewer Policy、valid packet validator、预算 / stop condition 和主 Codex 本轮明确裁决时，才可写 `Start required=yes` 并启动。pre-start 能力事实缺失时写 `Start required=no` 和 typed non-start `Start result`；已启动或启动后超时 / incomplete 时写 `Start required=yes`。
- 任一 pre-start 能力事实缺失时，记录 typed non-start result：`tool-unavailable / runtime-policy-blocked / explicit-delegation-required / packet-invalid / brief-invalid / validator-failed`；用户明确拒绝或撤销 reviewer 启动时记录 `explicit-denied`；并执行本地 fallback。已启动后未完成时记录 `review-incomplete / reviewer-timeout / budget-exceeded` 等 post-start incomplete result。

用途分界：
- 子 agent 的模型判断本身被用作验收、阻断、交付或豁免依据时，它是裁决性 Role Reviewer，受 G16、start authority、reviewer count、packet 和 disposition 约束。判定看用途，不看 `explorer / verification / worker` 等名称、task class、标签或调用工具。
- 只做搜索、定位、并行枚举或候选验证，且输出不进入上述裁决链时，它是机械性子 agent；启动时机、数量和调度交给官方工具，不支付 G16 / reviewer-count 税。
- 机械性输出只能作为线索，不得直接写成交付 PASS、无阻断、批准或 waiver 证据。主 Codex 可回到源码、测试或确定性 artifact 独立确认；若要使用该模型判断本身，必须先转入 Role Reviewer 合同。

Role-aware policy：
- `isolated reviewer` 可以按角色聚焦，不新增 Multi-Agent 状态源；角色只决定 reviewer 问什么，主状态仍是 `task_plan.md` / `findings.md` / `progress.md`。
- Brief 的 `role` 只是挑战焦点，不是编队编制。新 Brief 常用值：`requirements`、`security`、`release`；其它焦点写进 Brief 正文。packet validator 仍接受旧角色 token，避免已有 packet 因缩表失败。
- 默认启动数为 0；满足 Capability Fact Rule 后最多启动 1 个 reviewer；只有 G16 已路由且 `Risk Tier=release + Impact Scope=external-system`、风险面明显不同，才允许 2 个不同焦点 reviewer；超过 2 个必须用户明确点名并给出范围 / 时间 / token 预算。
- `campaign_count` 只统计 campaign artifact 数，不抵扣 reviewer 数，也不把 campaign 容器另算为 reviewer。任务级 reviewer 总数按当前裁决链中的独立裁决结果计算：standalone Role Reviewer 结果 + campaign 内各 role 结果 + `native-governed-reviewer` 结果；每个独立结果只计一次。
- reviewer 只输出 finding；不得输出新计划、新进度、新 owner / due date 列表，且不得维护第二套状态源。

Policy-Auto Read-Only Reviewer：
- `Policy-Auto Reviewer` 是内部只读 reviewer 的 start authority，不是档位税。G16 已路由且 Capability Fact Rule 满足时，内部 Codex 只读 reviewer 可用 `policy-auto`，不必每次再问用户；当前仅对 high / release / external-system 任务开放。档位本身不触发 assessment、不优先 reviewer、不构成启动理由。
- `policy-auto` 只适用于内部 Codex 只读 reviewer：repo-read、diff / evidence / waiver / release-source review；不得写文件、修改三文件、部署、push、访问 secrets 或创建第二状态源。
- `policy-auto` 是项目级预授权，不能覆盖 system / developer / tool policy，也不能把项目预授权等同为用户显式委派。实际启动内部 Codex subagent 前必须同时满足项目 start authority 和当前运行时工具调用政策。
- 官方工具若支持强制 read-only sandbox / permission narrowing，启动 Role Reviewer 时必须使用；prompt 中的“只读”不能替代执行层收窄。当前工具无法把主会话权限强制收窄到只读时，记录 `runtime-policy-blocked`、`Start required=no` 和本地 fallback，不得启动。
- 外部模型 reviewer（Gemini / Claude / 第三方 CLI/API）不自动等同于 `policy-auto`；必须使用 `external-standing-opt-in`、任务授权或会话授权，且只能读取脱敏 packet。
- implementation worker、写代码、deploy / DB write / push / external-write、secrets 访问、超过 reviewer 数量上限，仍需用户明确授权。
- 术语收敛：`Role Reviewer` 是实际只读子 agent；`Multi-Agent Role Assessment` 是是否需要 Role Reviewer 的评估记录；`Policy-Auto` 是内部只读 Role Reviewer 的 start authority；`enhanced-review` 是 code review 风险档位；`Review / Audit Boundary` 是从审查转实现的写入授权门。implementation worker 不是 Role Reviewer 的一种；默认不存在，只有用户另行授权且写入范围隔离时另案启用。

Role Trigger Matrix：
当 G16 已选择时执行。本表是启动策略，不是 G16 trigger。Trigger 以 Gate Card 为准。

| 场景 | 策略 |
|---|---|
| fast path / low | 不启动子 agent；只允许 `micro-local-check`，除非用户明确要求只读 reviewer 且 start authority / runtime policy 允许 |
| standard 普通改动 | 默认不启动；仅 G16 信号时可评估 1 个 `requirements` 或 `security` reviewer |
| high | 默认不记录 assessment、不启动；仅 G16 信号（显式只读挑战或验后仍有具体 residual semantic risk）时评估 |
| high + auth / DB / data flow / core behavior | 这些风险面可以写进 residual semantic risk；它们单独不打开 G16 |
| release | 默认不记录 assessment；交付/ship 仍走 G17。仅 G16 信号时评估 |
| Risk Tier=release + Impact Scope=external-system + deploy/auth/DB/dirty/waiver/长会话 | 可把具体残余风险写入三文件，从而产生 G16 信号；不因档位本身标 preferred 或 policy-auto 启动 |
| 批量独立文件 / package / incident 审计 | 可用只读 batch reviewer；写入 worker 默认禁用 |
| implementation worker | 默认禁用；只有用户明确授权且写入范围完全隔离时试点 |

Required assessment：
- Trigger 以 G16 Card 为准。G16 已选择后才评估并填写 `## Isolated Reviewer`。必须评估不等于必须启动。high/release/external-system 单独不打开评估。
- 启动决定归属看谁作出“要进行这次 reviewer”的决定：主 Codex 主动建议、请求或论证需要 reviewer，用户随后批准或代为转发，仍是 Codex 发起并走 G16；用户在 Codex 建议前已独立决定送审，Codex 只按要求整理材料，则是用户发起，不要求 Codex 启动 assessment 或强制 role-review packet。代写材料本身不构成发起。
- 用户发起只豁免 Codex 启动税：材料仍遵守脱敏与最小输入边界；finding 回流后仍按 Evidence Level、逐条 disposition 和 Review Finding Closure Map 收口。Codex 已作出启动建议时，不得用“请用户代转”改写为用户发起。
- 有 active 三文件写权限时记录到 `progress.md`；`review-only / plan-only` 且无三文件写授权时记录到最终回复或指定 `report-write-only` artifact。G00 的 review→write 授权边界不受影响。
- G16 已路由后，内部只读 reviewer 只有在 Capability Fact Rule 全部满足时才可按 `policy-auto` 启动，不再逐次询问用户；当前仅对 high / release / external-system 任务开放。外部模型 reviewer、写入、deploy、DB、push、secrets 或超过数量上限仍需用户明确授权。
- `Authorization scope` 固定为 `none / policy-auto / task / session / external-standing-opt-in / revoked`。`policy-auto` 来源是 `AGENTS.md Policy-Auto Reviewer`，仅用于内部 Codex 只读 reviewer；`task` / `session` 来自用户明确授权；`external-standing-opt-in` 来自项目级外部模型 opt-in，并写入 `Authorization source`。这些授权都不是永久全局授权，必须绑定当前 active task / run_id / repo path，任务切换、目标路径变化、权限扩大、跨会话恢复或进入 external-write 时自动失效。
- `preferred + Authorization scope=policy-auto/task/session/external-standing-opt-in` 还不够；只有 Capability Fact Rule 全部满足时，`Start required=yes`。若 pre-start 能力事实缺失，写 `Start required=no` 和 typed `Start result`（`tool-unavailable / runtime-policy-blocked / explicit-delegation-required / packet-invalid / brief-invalid / validator-failed` 等）、具体原因和 fallback；用户明确拒绝或撤销 reviewer 启动时写 `Authorization scope=revoked`、`Start required=no`、`Start result=explicit-denied` 和拒绝证据。`packet-invalid / brief-invalid / validator-failed` 必须有 packet validator 证据，`tool-unavailable / runtime-policy-blocked / explicit-delegation-required` 可在 packet 创建前记录。若已启动但超时 / 中断 / incomplete / 预算耗尽，写 `Start required=yes` 和 `review-incomplete / reviewer-timeout / budget-exceeded` 等 post-start result。不得再用“未授权”作为 unavailable 理由。旧 `started / unavailable / incomplete / not-authorized` 只作为兼容读取，新记录使用 typed start result。
- `policy-auto` 启动前必须有 valid Agent Brief、valid Reviewer Policy 和 valid packet。Agent Brief 约束“本次 reviewer 要回答什么、属于什么 task class、何时停止、是否拥有状态”；Reviewer Policy 约束“能做什么”。Agent Brief 缺失、stop condition 空泛、ownership 越权或 task class 为 `scoped-implementation` 时，不得启动，只能记录 `brief-invalid` / `packet-invalid` 并走 fallback。
- reviewer / campaign 必须记录 `runtime_enforced_budget` 或等价说明：区分 hard-timeout / hard-turn-limit / hard-file-limit 与 prompt-soft-limit / manual-fallback，避免把软 stop condition 误当执行层硬限制。
- 如果优先 isolated reviewer 但未启动，必须记录 typed non-start result / fallback，或给出明确 `not-needed` 理由；不得静默跳过。
- 干净的 `assessment-only / not-needed` 路径使用现有 `## Isolated Reviewer` 表的六项紧凑记录：`Required assessment=yes`、`Trigger decision=assessment-only|not-needed`、具体 `Reason`、`Authorization scope=none`、`Start required=no`、`Start result=not-needed`。未尝试启动时可省略 reviewer tool、runtime policy、packet、budget、verdict 等启动字段；只有 unavailable / incomplete / invalid / denied 等异常路径才要求 fallback。不新建第二种 non-start schema。
- 如果当前运行时工具政策限制未满足，主 Codex 不得调用 subagent；记录 `Authorization scope=policy-auto`、`Runtime policy status=explicit-delegation-required` 或 `runtime-policy-blocked`、`Start result=explicit-delegation-required` 或 `runtime-policy-blocked`、本地 S0/S1 fallback。不得记录为 `tool-unavailable`，也不得写成“policy-auto 未授权”。
- assessment 结构校验入口：`.agents/scripts/validate-reviewer-assessment.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger --format json`。仅在已有 reviewer 路由信号时校验表结构，不因 high/release 单独强制填表，不启动 reviewer。
- docs / copy / comments、formatting、小 bug、低风险重构、已知模块 focused test fix 不默认触发。

Native review service recognition：
- 仓库托管平台、IDE 或官方工具自动产生的审查结果默认是 `native-advisory`：评论可以作为线索进入 G19 code review，但它本身不满足 G16，不占 reviewer slot，也不能单独支持验收、阻断、交付或 waiver。若要把其模型判断本身放入当前裁决链，必须升级为 `native-governed-reviewer`。
- 只有以下六项全部满足，native result 才可记录为 `native-governed-reviewer`：
  1. 结果绑定当前 repo、PR（或等价 change request）、head SHA、审查范围和问题；过期 revision、base-only SHA 或范围不明的结果只能作为 advisory。
  2. 有当前任务授权，或有可证明且仍覆盖当前 repo / task 的 standing opt-in；G16 / `policy-auto` / task / session / `external-standing-opt-in` 或用户独立发起的授权来源已记录。
  3. reviewer 路径是只读的，审查输入、适用 instructions 和 MCP / connector 使用均可审计，并遵守最小输入与脱敏边界；不能读取 secrets、未脱敏 trace 或越过已授权 repo/path。
  4. 完整且可归因的审查输出被持久保存并可稳定引用；只有 check 状态、摘要徽标或不可回读的 UI 结论不够。
  5. finding 由主 Codex 逐条标注 Evidence Level、执行 disposition，并由 Review Finding Closure Map 连接 finding、fix 和 verification。
  6. native Comment 始终只是 finding 输入，不等同于 Approve、merge、ship 或 waiver authority；native 工具不得自行成为最终裁决者。
- 进入当前裁决链的每个独立 `native-governed-reviewer` 结果计 1 个 reviewer slot，并纳入已有任务级 reviewer 数量上限与预算；平台并发 cap 不能替代该预算。同一 native tool 针对较新 SHA 的重跑在当前裁决链中替换其旧 SHA 结果，不累计 slot；旧结果只保留为历史，不能与新结果同时计票。不同工具或其它彼此独立的当前结果各自计数。
- native comment、check 或平台身份不会自动把 evidence 提升为 `direct`。评论引用的代码行、实际命令输出或可复现缺陷，经主 Codex 独立核验后可记为 `direct`；纯模型判断、不可回放摘要或未复核推断只能记为 `indirect / unverified`。
- standing opt-in 或 repository ruleset 触发的自动 re-review 仍有真实成本，即使运行不经过本地账本；配置自动重跑时应考虑该成本。本合同不为此新增观测账本，也不新增 native-equivalence record/schema；复用现有 assessment、Role Review Summary、disposition 与 closure surface。

Review packet：
- 启动前由主 Codex 在 `.agent-state/runs/<run_id>/role-review/<role>/` 准备受控 packet；旧 `.agent-state/runs/<run_id>/isolated-review/` 只作为兼容路径读取。角色以 `Agent Brief.role` 为准，不再从目录名或 `Review Scope` 派生。
- 最小文件：`review-packet.md`、`diff.patch`、`changed-files.txt`、`evidence-ledger.md`、`waivers.md`、`dirty-worktree-summary.json`。
- `review-packet.md` 至少包含 Task、Risk Tier、Impact Scope、Goal、Negative Constraints、Files to review、Evidence、Reviewer task。
- `review-packet.md` 的 `Agent Brief` 是 reviewer 启动合同，也是唯一角色来源：`role`、`task_class`、`goal`、`context`、`ownership`、`output_format`、`stop_condition`。只读 packet 的 `task_class` 仅允许 `exploration / review / verification / handoff`；`scoped-implementation` 不属于只读 Role Reviewer packet，未来若支持写入 worker 必须另建 packet 和显式授权规则。
- `Agent Brief` 的 `ownership` 在只读 / policy-auto 下只能是 `finding-only` 或 `no-state-ownership`；子 agent 不拥有计划、进度、完成判断、三文件或代码写入权。
- `Agent Brief` 的 `stop_condition` 必须包含明确刹车条件，例如 `max files`、`max time`、`max findings`、`packet insufficient` 或 `secret suspicion`；“finish review” 这类空泛停机条件无效。
- packet 只放 task contract、当前 diff、Changed Files Manifest、Final Evidence Ledger、waiver、dirty summary、rollback / deploy evidence 摘要。
- 需要 behavior 摘要时，只能从 `task_plan.md` 派生 `role-review-scenario-packet.md` 只读快照；唯一权威源仍是 `task_plan.md`，快照不得成为第二套 behavior contract。
- 不放完整聊天历史、无关长日志、原始 `.env` / `.env.*`、私钥、token、production credentials、未脱敏 HAR / trace、数据库 dump。
- 如果 reviewer 需要判断 secret 是否误提交，只给文件路径、git status、dirty classifier 结果或已脱敏摘要。
- packet 结构校验入口：`.agents/scripts/validate-role-review-packet.py --root <project> --packet .agent-state/runs/<run_id>/role-review/<role> --format json`。旧 `.agent-state/runs/<run_id>/isolated-review` 只作为兼容路径读取。它只检查必需文件、脱敏边界、Agent Brief、Reviewer Policy、Output Contract 和 finding 结构，不启动 reviewer。`--strict` 或 `--risk-tier high|release` 会额外要求完整 `Agent Brief`、`Output Contract` 与 `Review Evidence Index`；light reviewer packet 可以省略这些 strict 表。

Review posture and falsification：
- 裁决性 Role Reviewer 保持 evidence-neutral，并默认 falsification-first：先尝试证伪送审声明，而不是寻找确认性措辞。语气不要求对抗，severity 仍由 Evidence Level 约束；S0 / S1 必须有 `direct` evidence。
- packet 路径的机器可读 `verdict=pass` 只表示：在已声明范围和已执行探针内没有发现 material falsifier；它不是正确性证明。pass 必须包含至少一项 `falsification_attempts`，逐项记录 `hypothesis / probe / evidence / outcome`，其中 evidence 绑定 packet 内已声明的 check 或 artifact。
- attempt outcome 只允许 `excluded / not-reproduced / not-applicable`。pass 的 attempts 不得全部为 `not-applicable`；无法形成可执行证伪路径时记录 `verdict=review-incomplete`（reason=`packet-insufficient`），不得输出 pass。非 pass verdict 不强制 attempts。
- 已执行但未成立的证伪尝试本身是有效审查结果。不得用 finding 数量、阻断率、语气强度衡量 reviewer 质量，也不得为了表现“对抗性”制造或抬高 finding。
- 角色只改变探针方向，不改变 schema：`requirements / plan-consistency` 优先找需求矛盾、遗漏验收和负向约束；`architecture` 优先找边界、不变量和耦合失效；`qa / release` 优先复现失败、负向路径、回滚与证据声明；`security` 在只读和脱敏边界内探测滥用、权限和输入边界；`knowledge / docs-api` 优先找事实陈旧、接口漂移和第二权威。`mixed` 只选择与当前风险直接相关的方向。
- 本结构只约束 packet 路径下的机器可读 pass；用户独立发起并人工转发的外部审查不因此被强制填写新表，但其 finding 回流仍遵守 Evidence Level、disposition 和 closure 合同。

Reviewer boundary：
- 只读：Read、rg / grep、git diff / status、三文件、evidence artifact 摘要。
- 禁止：Write / Edit、commit / push、deploy、docker compose up/down、数据库写入、访问 secrets、创建新计划或新状态源、自动改写主计划。
- packet 必须声明机器可读 `Reviewer Policy`：`repo_write_scope=none`、packet result artifact 边界、允许动作、禁止动作和 no-second-state-source；可用 `validate-role-review-packet.py` 校验。
- Role Reviewer 不得再委派任何子 agent，包括机械性 explorer / verification 子 agent。`Reviewer Policy` 必须声明 `subdelegation=none`，由 packet validator 校验；不得依赖某个工具当前不支持嵌套 spawn 来代替合同。
- 默认预算：只读当前 diff + 三文件 + evidence，不做全仓扫描，不追溯完整聊天历史，不生成新计划。
- 超过时间 / token / 文件范围时，标记 `review-incomplete`，不自动阻断。
- reviewer prompt 必须短且自包含，写清审查问题、文件范围、输出格式和预算；不要依赖中途 `interrupt` 后恢复上下文。
- 如果 high-assurance reviewer 超时或被打断后丢失上下文，按 `review-incomplete` / `reviewer-timeout` 处理，执行 fallback，而不是把残缺输出升级为 pass。

Review engine and reasoning-tier policy：
- 已授权启动的裁决性 reviewer 默认使用该工具映射中面向深度审查的最高常规档，记为 `high-assurance review tier`。映射必须显式且稳定；供应商新增档位不会自动改变映射，也不会自动升级已有 reviewer。
- `high / release / external-system` 继续使用当前 `xhigh`-equivalent 的 high-assurance 映射（工具支持时）。低于 high-assurance 档只允许因 `budget-capped` 或 `unsupported`，并在 Reviewer Execution Metadata 记录原因。
- `max / ultra / pro` 等供应商例外高价档只是示例；使用此类 exceptional tier 必须同时有显式预算声明和 `quality-priority=yes` 声明。档位可用本身不构成选择理由。
- review engine、model 或 reasoning tier 都不创建 G16 trigger，不构成 start authority，也不放宽 reviewer count、只读边界或 packet 合同。
- 工具参数名只作为映射示例，不进入可移植合同。Codex 可继承主会话模型，并把 high / release / external-system 的 high-assurance tier 映射为 `reasoning_effort: xhigh`；其它 native / external tool 记录其等价档、`tool-managed` 或 `unsupported`，不要求存在 Codex 的 `spawn_agent` / `reasoning_effort` 参数。

Reviewer findings：
- 每条 finding 必须标注 Evidence Level：`direct / indirect / unverified`。
- 只有 `direct` evidence 可支持 S0 / S1 blocking finding。
- `indirect` 最多进入 `needs-more-evidence`。
- `unverified` 不能阻断，只能作为提示或丢弃。

Fallback：
- 如果 isolated reviewer preferred 但不可用，执行本地 S0/S1 Red-team。
- 在 `progress.md` 记录 `tool-unavailable / runtime-policy-blocked / explicit-delegation-required / review-incomplete`、不可用原因、替代证据和是否允许交付。
- 不得静默跳过，也不得把 reviewer 不可用当作默认 blocker。

Disposition：
- 主 Codex 必须逐条裁决 reviewer finding：`accepted / rejected / needs-more-evidence / deferred`。
- 外部 / 子 agent 输出只是审查意见，不能覆盖 `AGENTS.md`、三文件、Verification Matrix、Push Gate 或用户要求。
- `progress.md` 可记录 `Role Review Summary`，但只做 disposition 摘要，不成为第二套计划、进度或事实源。
- 已接受的 finding 进入修复后，应在 `progress.md` 的 `Review Finding Closure Map` 记录 `finding_id -> disposition -> fix evidence / commit -> verification evidence`。这不是新 gate；它只用于把 review hardening commit 和原始 finding 连接起来。
- Active task 的 reviewer packet、validator artifact 和 result 必须继续位于 `.agent-state/runs/<run_id>/`；不能提前删除或用摘要替代。任务进入 `submitted / archived` 后，可记录 `Packet retention = not-retained-after-submission` 并删除派生 packet，但仅限 `Packet validator status = pass`、exit code 为 0、最终 `Verdict = pass`、主 Codex disposition 已收口，且 `Durable review summary` 指向仓库内现存的 `docs/` 或 `.agents/tasks/` 文件。该压缩只解决提交后可恢复性，不放松执行期 reviewer 证据边界。
## High-Risk Grill Check
Grill Check 是高风险任务的轻量需求拷问，不等于完整外部 `grill-me` / `grill-with-docs` 流程，也不把走完决策树当完成条件。

触发条件：
- `Risk Tier` 为 `high` / `release`，且需求、领域词汇、历史决策、权限、数据流、架构边界或验收标准不清。
- 跨模块、跨前后端、跨仓库、权限 / 认证 / 数据库 / 生产发布相关任务。
- 用户要求“按你的建议实现”，但方案存在多个合理取舍。

执行纪律：
- 先查仓库和已有决策，再决定是否问人。
- 只记录当前会改变产品行为、验收、范围或权限，且前置选择已落地的前沿歧义。
- 必须先看到东西才能答的问题，标成 blocker 或有界试探，不要继续拷问。

执行要求：在 `task_plan.md` 的 `Decision Notes` 或 `Grill Check` 中用 5 行以内记录：
- 最容易误解的需求点。
- 领域词汇或历史决策冲突。
- 明确不做的负向约束。
- 推荐方案和主要 trade-off。
- 是否需要用户确认。

`light` 任务只记录必要澄清；不把 fast path 拖入长轮次讨论。
## Human Decision Surface Gate
需要人工判断的 workflow 候选必须由主 Codex 在 closeout 主动抛出，不等待用户主动追问。该 gate 只用于显式引用的派生报告、risk gate、review finding 或 workflow 进化候选；普通 fast path / low 任务不得因此升级。若机制已有专用 closeout surface（例如 Skill Curator Closeout），使用专用 section，不要重复写入通用 `Human Decision Surface`。

决策等级：
- `record-only`：只记录候选或收益信号，不问用户，不阻断。
- `surface-required`：最终回复或 closeout 必须主动列出 bounded question / disposition；缺失时 strict closeout 失败。
- `answer-required`：没有用户明确回答，不得执行对应改动；如果该动作是交付必需，closeout 只能 blocked / deferred。
- `risk-acceptance-required`：高风险交付、release source blocked、S0/S1 未解决、外部写入、DB、deploy、push、secrets、plugin/MCP/hook/install/globalize 等必须显式接受风险；不能默认接受。

必须主动抛出的场景：
- `workflow-value-report.py` 产生 `human_decision_required=true` 或 `human_decisions[].decision_level=surface-required/answer-required/risk-acceptance-required`，且报告被本轮三文件引用。
- `skill-curator-report.py` 产生 `human_needed` 时使用 `progress.md#Skill Curator Closeout`，它是专用 human-decision surface；不要同时复制到通用 `Human Decision Surface`。
- review-only / audit / plan-only 转 implementation/write/deploy/commit/push。
- Requirement Reconciliation 需要人工判断、release source blocked、S0/S1 未处置、Sensitive Operations 或 external skill/plugin/MCP/hook/install/globalize。
- 准备删除、弱化、默认化、全局化、安装或扩大权限任何 workflow gate、skill、plugin、hook、Structural Index / Graphify / CodeGraph 行为。

`Human Decision Surface` 记录必须包含：`decision_id`、source、level、surfaced、default recommendation、bounded options、disposition、authorization scope 和 evidence。保守默认值应优先是 `record-only`、`defer`、`narrow-trigger`、`ask-user` 或 `blocked`；不能把 `record-only` 当作写入 / 发布 / 安装授权。任何 `user-approved` disposition 必须写明授权范围。
