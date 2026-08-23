# Workflow Module: verification-evidence

Runtime authority: detailed reference only; project `AGENTS.md` remains routing authority.
Default loading: no; read only when the matching gate or task phase is active.
State boundary: no task state, runner authority, or delivery approval.

## Verification / Evidence
复杂任务的验证必须写成矩阵，而不是一句“已测试”。

- `low`：记录直接相关的最小验证。
- `standard`：至少记录 focused test / lint / typecheck 中与改动匹配的项。
- `high`：记录自动化验证、人工 QA、文档/配置同步、回退点和未验证风险。
- `release`：额外记录发布前置项、环境确认、回归范围、release note、变更清单和回退点。

Evidence rule：
- 输入 revision、命令、范围和环境均未变化时，重复运行已通过检查不产生新证据；迭代中选择与改动面匹配的最窄入口。项目声明的 merge / release baseline 仍须在最终候选 revision 上运行一次。
- 必需验证必须有 evidence：命令、exit code、`.agent-state/runs/<run_id>/...` artifact、截图路径、trace/report、接口响应摘要或人工 QA 记录；旧 `.agents/runs/<run_id>/...` 只做兼容读取。
- 工具运行的详细 stdout / stderr / JSON 优先写入 `.agent-state/runs/<run_id>/`；`progress.md` 只写摘要、结果和 artifact 路径。
- `.agent-state/runs/<run_id>/manifest.json` 是 run 索引。`high` / `release`、artifact-bearing run、或被 Final Evidence Ledger 引用的当前 run 应有顶层 manifest；旧 run 缺 manifest 只做 legacy warning，除非显式按 current evidence 严格检查。
- 每个验收项必须映射到至少一种 evidence method。
- “已测试”“看起来正常”“肉眼看过”这类没有命令、artifact、截图、trace、API 响应或人工 QA 记录的表达不算 evidence。
- `optional` 或明确 `not-needed` 的检查不需要长篇 waiver。
- 必需验证失败、超时、不可运行或被替代验证覆盖时，写入 `progress.md` 的 `Verification Waivers`。
- `release` 级 UI / 浏览器改动必须在 `progress.md` 的 `Browser / UI Evidence` 记录截图、trace、report、CDP check 或跳过原因。
- UI、浏览器、Chrome 扩展或人工 QA 任务如果存在手工步骤，应在 `Manual Validation Checklist` 记录 `manual_check_id`、步骤、状态和证据。standard 任务可只写简短 manual note；release 任务需要可复核 artifact 或明确跳过原因。
## Pre-existing Failure Claims
声称某项失败为 `pre-existing` 时，必须引用同一命令、同一范围在改动前 revision 或 clean-base worktree 上的 manifest / artifact 作为基线，并与当前结果比较。

- 只有在基线中可稳定匹配的失败才能记为 `pre-existing`。
- 基线之外的新增失败记为 `candidate-new`，仍需归因与处置。
- 无基线证据时记为 `unverified-pre-existing`：不得据此忽略该失败或支持 PASS；必须选择 clean-base 复跑、修复，或填写完整 typed waiver。
- 同一失败签名在数量、严重度或位置上恶化时，不能以“基线中也有类似失败”豁免。
- flaky 或环境不一致场景下，单次基线运行不能冒充归因证据。
## Test Evidence Gate
当 G10 已选择时执行。Trigger 以 Gate Card 为准。这是高风险行为变更的证据闸门，不等于强制所有任务完整 TDD。普通 focused bugfix 只需记录修复前复现和修复后回归证据，不要把完整 Test Evidence Gate 当成已命中。

执行要求：
- bugfix 优先先有失败复现：失败测试、失败命令、API 响应、浏览器步骤、截图 / trace 或人工可复现记录。
- 核心逻辑优先行为测试或公共接口测试；项目已有测试基础时优先 red-green 证据。
- 跨层改动至少有端到端路径证据：API smoke、浏览器回归、集成测试或人工 QA 记录。
- 记录 `Test-first decision`：`red-green / characterization-before-code / pre-fix-reproduction / post-change-only-with-waiver / not-testable / not-needed`。这不是全局 TDD 授权；只是说明为什么先写、先复现、先刻画或无法先测。
- 选择 red-green、回归闭环、高风险缺陷、核心 / 跨层 / 权限 / 字段 / 迁移改动，或普通 focused bugfix 缺少明确 pre/post evidence 时，记录 red-green anti-overfit fields：`pre-fix command`、`expected failing assertion`、`post-fix command`、`same scenario_id` 和 `risk case covered`。red 阶段必须失败于目标行为缺失，不是 fixture、编译或 mock 配置问题。普通 focused bugfix 已有修复前复现和修复后回归证据时，不强制填写完整 red-green 表。
- 防测试过拟合：不要只用默认值 / 巧合值或一组 happy path；优先用参数化样例、边界 / 负向 / 权限拒绝、契约验证、property / invariant 或人工审阅 golden 作为反向信号。
- 无法测试时必须写入 `Verification Waivers`：原因、替代证据、owner、后续动作和允许交付条件。
- 不为了满足形式写脆弱 mock 或实现细节测试；测试应验证外部可观察行为。
## Test Strategy Ladder
按改动类型选择最小必要测试阶梯，不默认全量测试。

| change type | 最小测试阶梯 |
|---|---|
| 文档 / 规则 / 模板 | diff review + smoke / contract |
| 纯前端展示 / UI | 静态检查或构建 + 目标页面浏览器回归；release 级记录 Browser / UI Evidence |
| API / 服务逻辑 | focused unit / service test + 目标接口 smoke |
| 数据库 / 迁移 / 数据修复 | dry-run / schema check + 目标表备份或回退点 + focused data verification |
| 认证 / 权限 / 租户隔离 | 正向 + 反向权限验证；不得只跑 happy path |
| 跨前后端 / 三端联调 | 后端 focused test + 前端构建/页面回归 + API/浏览器端到端证据 |
| 部署 / 生产回归 | 构建产物校验 + 备份/回退点 + 健康检查 + 目标业务链路复验 |

`high` / `release` 行为变更应优先满足 Test Evidence Gate；没有测试基础时记录 waiver，不强行搭建无关测试体系。
## Workflow Trace
复杂任务必须在 `progress.md` 中记录实际流程轨迹：
- risk_tier、impact_scope、read_before_decide。
- requirements-to-plan、tooling-map、tooling-router、verification_matrix、test_strategy。Direct orientation 由 `read_before_decide` 表达；三文件自身和 active snapshot 已表达 active state，不再新增 wrapper 替代行。
- Graphify、ship-check、code_review、isolated_reviewer、red_team、sensitive_guard、push_gate。
- 按实际使用状态记录，不把未运行工具写成已通过。

Workflow Trace consistency / trajectory eval：
- 吸收 dynamic workflows / agent eval 的 trajectory / tool-use 思想，但不引入 Claude Dynamic Workflows、LangGraph、CrewAI、AutoGen 或默认 `workflow-runner-lite`。
- `Workflow Trace` 是路径一致性摘要，不是第二状态源，不替代 `Validation`、Acceptance Evidence、`Final Evidence Ledger` 或 run manifest。core `progress` 默认不带此表；需要轨迹诊断时从 appendix 拷入。
- 派生 trace JSON 只能放在 `.agent-state/runs/<run_id>/workflow-trace.json`，必须标注 derived metadata；不要在项目根创建 `workflow_trace.json`、`workflow-plan.json` 或 `workflow-run.json`。
- 默认只做 deterministic consistency check 和静态 trajectory fixtures；live LLM eval、trace grading、外部模型对比只允许显式专项评估，不进默认 CI，也不作为 release 阻断。
- 结构检查入口：`.agents/scripts/validate-workflow-trace-consistency.py --root . --task-plan task_plan.md --progress progress.md --strict-trigger --format json`。
- 典型检查：review-only 任务不得出现实现证据；policy-auto reviewer 必须有 valid packet / Agent Brief / validator artifact / Role Review Summary；release artifact 不能跳过 source gate；Graphify refresh 必须有显式授权；根目录不得出现 workflow trace/plan/run JSON 状态源。
- `Ship Check` 交付结论必须和普通 test/build pass 区分；`delivery recommendation=no/not-ready/blocked` 不能因为同一 section 有 `test pass` 被当作可交付。
- `Run Evidence` 的当前列名是 `tool / command`、`manifest / artifact`、`status`；legacy `command / check`、`result`、`conclusion`、`exit_code=0` 仍作为兼容输入参与 stale trace 检测。

Agent-view debugging / trajectory intake：
- 只复用现有 `Workflow Trace`、Run Evidence `manifest.json`、`Trace-to-Eval Intake`、Role Review Packet 和 Human Decision Surface；不得创建独立 `agent-view-debug` packet、root debug JSON、runner、memory 或第二状态源。
- 触发范围仅限 high / release / external-system、review / audit replay、workflow source changes、重复 tool misuse / failure-loop、显式用户要求；普通 fast / low / standard 小任务不为此新增记录负担。
- `Workflow Trace.notes` 可用紧凑 key/value 记录 agent 视角：`expected=...; actual=...; failure_class=...; artifact=.agent-state/runs/<run_id>/manifest.json`。只写机制差异和证据指针，不粘贴完整聊天历史、raw logs、HAR、secrets、账号、生产数据或大段工具输出。
- 如果该视角揭示真实 workflow miss、routing gap、validator gap、tooling gap 或 over-claim，收口时写入 `Trace-to-Eval Intake`，并按 Real Project Audit Epoch Preflight 标注 `task_epoch` / `audit_lens` / `attribution_type`；它只是候选，不自动生成 eval、不进入默认 CI。

Dynamic Agent Campaign：
- Campaign 只是 `.agent-state/runs/<run_id>/multi-agent-campaign/` 下的派生 artifact，用来记录 2+ role reviewers、显式 dynamic-agent 实验、campaign metrics 收集或 broad audit slices；不是 runner、不是授权模型、不是第二状态源。
- 单个 Policy-Auto reviewer 默认继续使用 `.agent-state/runs/<run_id>/role-review/<role>/` 和 `progress.md#Role Review Summary`，不创建 campaign，除非明确收集 campaign metrics 或运行实验。
- Campaign 必须包含 hard budgets、role packet validator artifacts、main Codex disposition、metrics；external reviewer campaign 必须先有 standing/explicit opt-in 和 sanitizer-pass evidence。
- 结构检查入口：`.agents/scripts/validate-dynamic-agent-campaign.py`（source-assurance / `--include-assurance` only）`--root . --campaign .agent-state/runs/<run_id>/multi-agent-campaign --format json`。默认 Base 不安装此脚本。

Live Eval Experiment Profile：
- Live LLM eval、trace grading 和 external evaluator comparison 只允许显式专项实验，不是默认 runner、默认 CI、ship-check、closeout、release blocker 或第二状态源。
- 实验准入 profile 只放在 `.agents/evals/live/live-eval-experiment-profiles.v1.json`，由 `.agents/scripts/live-eval-profile-report.py`（source-assurance / `--include-assurance` only）`--root . --format json` 做 report-only 结构检查；默认 Base 不安装此脚本。该脚本不启动 evaluator、不调用模型、不执行命令、不读取业务源码或 `$HOME/.codex`。
- 如果未来显式运行 live eval，结果只能作为派生 artifact 放在 `.agent-state/runs/<run_id>/live-eval/`，且必须标注 calibration-only；不得在项目根创建 `workflow_trace.json`、`workflow-plan.json`、`workflow-run.json` 或 live-eval result state。
- external evaluator profile 必须要求 standing / explicit opt-in，只能使用 redacted / sanitized packet、campaign metrics summary 或 disposition summary；raw chat、raw logs、secrets、HAR、DB dump、root workflow trace、business source tree 禁止作为默认输入。
- live eval 分数只能用于校准和实验复盘，不能替代 deterministic validators、Role Review disposition、Final Evidence Ledger 或 release source provenance。
## Reward-Hacking / Held-Out Boundary
Reward-hacking checks are workflow-source repair inputs, not default delivery gates. When changing validators, evals, benchmark catalogs, reports, or gate rules, check whether the change measures real task success or only makes a visible grader easier to satisfy.

- Public benchmark, advisory catalog, smoke, and visible behavior fixture results are not held-out evidence. A public benchmark result must not be described as held-out proof, release evidence, delivery approval, risk acceptance, or human authorization.
- Validator / eval changes should include positive, negative, and no-trigger or boundary coverage when the change affects workflow-source behavior.
- Do not optimize for a single exact trace path when multiple valid paths satisfy the workflow contract.
- Do not allow evidence-free PASS, unmatched WAIVED, self-reported completion, editable expected output, or fixture-only score improvement to count as workflow value.
- If a workflow-source change could be gamed by editing a grader, fixture, report, or validator instead of improving behavior, record the risk in the relevant eval/case notes or workflow-source attribution appendix.
## Release Artifact Source Gate
当 G18 已选择时执行。Trigger 以 Gate Card 为准。`release` 或 `external-system` 任务如果产出 jar / dist / container / 部署包，必须能说明产物从哪组源码状态构建。工作区存在 dirty source / doc、生成物、部署包或协作脏状态时必须填写；干净工作区也要记录 `clean-source-build`。

适用的发布包冒烟应从仅含待发布产物的仓库外临时目录安装并执行，确保不能回退解析 workspace、源码树或未打包文件。

允许模式：
- `clean-source-build`：产物从 clean commit / clean worktree 构建，并记录 clean source / git status evidence。
- `source-manifest-build`：产物从 dirty worktree 构建，但已记录 source manifest、artifact sha256 和 dirty source 摘要。
- `allowed-diff-build`：已记录允许进入产物的 source diff 范围，并由 ship-check / reviewer 确认无关 source 改动未进入 artifact。

最小证据包写入 `.agent-state/runs/<run_id>/release-source/`：
- `git-status-short.txt`
- `git-diff-stat.txt`
- `changed-files.txt`
- `changed-source-files.txt`
- `intended-source-files.json`
- `allowed-source-scope.txt`（legacy compatibility；新包不能只依赖它）
- `source-manifest.json`
- `artifact-sha256.txt`
- 可选 attestation artifact：`attestation.*`、GitHub attestation verification transcript、SLSA provenance 或 npm provenance transcript；未启用时写 `attestation mode=local-only / not-needed`。

规则：
- `progress.md` 只记录 release-source 目录、source mode、artifact sha256 和结论，不粘贴长清单。
- 常用起点：`git rev-parse HEAD`、`git branch --show-current`、`git status --short`、`git diff --stat`、`git diff --name-only`、`sha256sum <artifact>`。
- dirty worktree 下的新 `source-manifest-build` / `allowed-diff-build` 必须包含 `intended-source-files.json`，用 repo-relative path、per-file sha256 和 reason 说明哪些源文件被有意纳入产物。
- `source-manifest.json` 必须至少包含 `build_command`、`created_at`、`artifact_sha256` 和 `changed_source_files`；不能只放一个可解析的占位 JSON。
- Attestation mode 可选值：`local-only / github-attested / slsa / npm-provenance / not-needed`。默认 `local-only`，只有项目 CI / registry / release 流程已经启用对应机制时才要求验证；attestation 不替代 source manifest、artifact sha256 或 dirty-source 处置。
- `allowed_source_files`、`allowed_source_scope` 或 `allowed-source-scope.txt` 只作为旧包兼容字段；新 release packet 的充分证据是 `intended-source-files.json` 和 `source-manifest.json`。新任务不得把 `allowed-source-scope.txt` 当作主证据；validator 对 legacy path 保持兼容读取并报告 `legacy_source_scope_used` warning。
- 可选强路径：用 `git worktree` 建 clean build workspace，再只应用本次允许发布的 patch；这不是默认要求。
- 不强制 `git stash`、`git reset` 或清空工作区。
- 如果三种模式都不满足，部署默认 blocked；只有 `Source mode=blocked`、用户明确 `explicit user risk acceptance`，并写入完整 `Verification Waivers` 后才可条件继续。
- 机器级回归入口：`.agents/scripts/validate-release-artifact-source.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger`，用于验证 `Release Artifact Source Gate` 和 release-source packet 的一致性；它只检查证据，不生成证据或执行部署。
- `--strict-trigger` 下，`release` / `external-system` 且 artifact 为 `jar / dist / container / package` 时，不得把 gate 写成 `Required=no` 或 `Source mode=not-needed`；`external-system` 可以来自 `Risk Tier` 区块里的 `Impact Scope` 字段。
- `risk-accepted` 必须使用 `Source mode=blocked`，并能链接到 `Verification Waivers` 中完整的 release artifact source waiver；waiver 的 `allowed to ship` 只能是 `yes` 或 `conditional`，`no` 不构成条件放行证据。
## Evidence Reconciliation
最终交付前，复杂任务应把分散的验证结果合成唯一验收口径，避免 Matrix、脚本、人工 QA 和 waiver 各说各话。

- `Final Evidence Ledger` 放在 `progress.md`。
- `Requirement Reconciliation` 也放在 `progress.md`，只回答“实现和证据是否仍符合原始需求 / 非目标 / 负向约束 / 行为例子”。它不是第二套 ledger，不替代 `Final Evidence Ledger`。
- `Requirement Reconciliation.alignment_status=mismatch` 表示实现或证据偏离需求，必须修复、重新确认或 waiver；`needs-human-check` 表示业务语义无法由自动测试判定，必须请求用户 / 领域确认或记录 waiver。二者都不能和同一 acceptance 的无条件 `PASS` 并存。
- 每个验收项最终只能是：`PASS / MANUAL / WAIVED / FAILED / BLOCKED / NOT_APPLICABLE`。
- 如果通用矩阵显示 `MANUAL_RECHECK`，但补充受控脚本已覆盖，必须在 ledger 写明替代证据和 artifact。
- 没有命令、artifact、截图、trace、API 响应或人工 QA 记录的项不得标记为 `PASS`。
- 机器级结构检查入口：`.agents/scripts/validate-evidence-waivers.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger`。它只检查 `Final Evidence Ledger` 和 `Verification Waivers` 的状态枚举、证据占位和 waiver 完整性，不判断业务正确性。
- 机器级需求对账一致性检查入口：`.agents/scripts/validate-traceability.py --root <project> --task-plan task_plan.md --progress progress.md --strict-trigger`。它不会判断业务语义是否正确，但会阻止显式 `mismatch / needs-human-check` 与相关 `PASS` ledger 同时存在。
- `--strict-trigger` 下，`high` / `release` 任务必须有 `Final Evidence Ledger` 行；`WAIVED` 必须按 `acceptance_id` 匹配完整 waiver，不能复用无关的单条 waiver。
- `--strict-trigger` 下，blocking `Verification Matrix` 行必须能按稳定 id 匹配到 `Final Evidence Ledger`；不要用 `A1 foo` / `A1-bar` 这类未同步的后缀或描述差异绕过 ledger。
## Verification Script Capture
临时脚本只要作为交付证据，就必须可复现。

- 必须复制到 `.agent-state/runs/<run_id>/scripts/`，并记录命令、sha256、输入、输出 artifact 和来源路径。
- 推荐入口：`.agents/scripts/capture-run-script.sh --run-id <run_id> --script <path> --command "<command>"`。
- 如果脚本执行结果本身作为 PASS 证据，还要用 `capture-run-command.py` 捕获脚本执行命令并生成顶层 run manifest；脚本 capture metadata 不能替代 run manifest。
- 同一个脚本复用两次以上，或已成为项目稳定验证入口时，提升到 `.agents/scripts/` 或项目测试目录。
- `.codex-tmp/` 中未捕获的临时脚本不能作为最终交付证据；只能作为探索记录。
