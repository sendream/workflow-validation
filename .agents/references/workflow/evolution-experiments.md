# Workflow Module: evolution-experiments

Runtime authority: detailed reference only; project `AGENTS.md` remains routing authority.
Default loading: no; read only when the matching gate or task phase is active.
State boundary: no task state, runner authority, or delivery approval.

## Harness Stale-Assumption Register
Harness assumptions are reference-only review inputs. They are not state source, not backlog, not owner/due-date tracker, not live LLM eval trigger, and not a dynamic workflow runner. Use them during workflow refactors, model/tool/plugin upgrades, repeated real-task feedback, or explicit harness audits to decide whether a rule should stay strict, relax, move to optional, or be removed.

Field list: component_id, assumption, why it exists, validation signal, remove-or-relax when, owner file, last reviewed.

| component_id | assumption | why it exists | validation signal | remove-or-relax when | owner file | last reviewed |
|---|---|---|---|---|---|---|
| role-reviewer | Role reviewer default start count remains 0 unless risk-triggered or explicitly requested | protects fast path / low tasks from default multi-agent flow tax | accepted finding rate, missed-review incidents, and reviewer incomplete rate | real high/release data shows consistent positive net value with controlled token cost | `AGENTS.md`, `workflow/reviewer-governance.md` | 2026-06-13 |
| role-reviewer | Internal high-risk reviewer uses inherited model/version with high or xhigh reasoning | avoids cheap-reviewer false confidence on security/release decisions | accepted S0/S1 findings, false positives, and needs-more-evidence ratio | cheaper role model profiles prove equal quality on project evals | `code_review.md`, `role-review-packet.md` | 2026-06-13 |
| structural-index | Structural Index tools remain explicit query/trial paths, not default hooks | prevents generated graph/cache churn and context pollution | query result changed decision, source confirmation rate, elapsed time, and artifact size | several project pilots prove low overhead and high decision-change value | `AGENTS.md`, `workflow/tooling-safety.md`, `tooling-map.md` | 2026-06-13 |
| flow-tax | Live LLM eval and external reviewer comparison stay explicit experiments | avoids non-deterministic CI, privacy leakage, and release blockers from uncalibrated judges | calibrated eval reports, cost class, and human accepted/rejected rate | stable benchmark set and standing opt-in exist | `validator-map.md`, `workflow/evolution-experiments.md` | 2026-06-13 |
| flow-tax | Full template fields are mandatory only for matching high/release or explicit gates | keeps ordinary standard work from becoming documentation-first | task duration, skipped/not-needed noise, validator false positives, and user rework | compact tasks repeatedly miss important evidence | `.agents/templates/`, `workflow/routing-planning.md` | 2026-06-13 |
## Real Task Feedback Loop
- 真实任务暴露 workflow miss、validator 误报 / 漏报、重复 waiver、重复 failure signature、高价值 reviewer finding、证据缺口或知识沉淀遗漏时，收口阶段记录反馈候选。
- 反馈候选是派生改进输入，不是第二状态源、不是 backlog、不是自动 eval / skill / reference 生成器。
- 候选落点只允许：`eval-candidate`、`knowledge-candidate`、`metric-candidate`、`validator-candidate`、`none / not-needed`。
- 候选反馈必须带机制归因字段：`task_epoch`、`mechanism_id`、`introduced_at`、`workflow_synced_at`、`applies_from`、`source_baseline`。用 `legacy / migration / current` 区分旧任务、迁移期和当前机制样本；不要把机制引入前的历史任务直接当成当前机制负收益证据。
- Live Task Audit Mode：审计仍在执行的项目任务时，先标明 `audit_lens=active`，只评估根三文件、当前 run manifest 和当前证据链；不得用缺 archive / closeout 直接判定负收益。任务已提交但未归档时用 `audit_lens=submitted`，直接检查 Git / delivery facts；正式归档审计才用 `audit_lens=archive`，检查 `summary.md`、task archive hygiene 和 run manifest 可追溯性。`audit_lens` 是审计视角，不是状态源。
- Real Project Audit Epoch Preflight：审计真实项目 workflow 效果、统计正 / 负收益或准备把项目样本转成反馈候选前，先收集最小时间线：机制 `introduced_at`、项目 workflow `workflow_synced_at`、任务 `started_at / updated_at / completed_at`、样本证据来源和 `audit_lens`。临时分类为 `pre-mechanism / pre-sync / migration / current / unknown`；写入反馈表时映射为 `task_epoch=legacy`（pre-mechanism / pre-sync）、`task_epoch=migration`（同步窗口、active task 需迁移、证据跨版本）或 `task_epoch=current`（任务和证据均在机制生效后）。`unknown` 是 preflight 分类，不是候选行值；不能写入 Real Task Feedback 或 Trace-to-Eval candidate row，先补时间线证据。不要新增 `mechanism_epoch`，也不要把 `defer` 当成 `task_epoch` 值。只有 `current` 样本可以直接作为当前 workflow 缺陷 / 收益证据；`legacy` 和 `migration` 样本只能作为迁移报告、archive / manifest 补强、或带边界的候选信号。
- Epoch preflight 不新增表、validator、memory、runner 或第二状态源；继续使用 `findings.md#Real Task Feedback Loop`、`progress.md#Trace-to-Eval Intake`、`validate-knowledge-promotion.py`、`validate-active-task-migration.py` 以及 archive/run manifest 的 `--legacy-warn` 路径。
- 候选反馈必须带 `attribution_type`：`knowledge-gap / skill-defect / execution-lapse / validator-gap / reviewer-gap / tooling-gap / environment-debt / docs-drift / external-change / routing-gap / template-gap`，或 `not-needed`。归因只决定候选落点，不自动授权修改。
- `execution-lapse` 表示 agent 没有遵守已有有效规则；它不能直接推动 `local-skill`、`reference`、`template` 或 `knowledge-promotion` 更新。只能进入 reminder / common-pitfall / reviewer calibration / eval candidate / no-change 这类候选。
- `eval-candidate` 必须写明 positive fixture、negative / forbidden fixture 和 failure oracle，或引用已覆盖的 case。不要从单个失败样本直接生成全局规则。
- 只有后续明确的 workflow 维护任务才能把候选转成 eval fixture、reference 更新、validator 改动或 skill 改动。
- Trace-to-Eval Intake 只记录 expected behavior、observed behavior、source artifact、机制适用基线和候选 eval 类型；它不自动生成 eval，不进默认 CI，也不替代 `validator-map.md`。
- Reviewer Calibration Summary 用来衡量只读 reviewer 的实际收益：记录 started、findings_total、accepted/rejected/needs-more-evidence、evidence_levels、timeout/incomplete 和是否改变主计划；不要用它反向授权更多 reviewer。
- Workflow Value Report：source-assurance / `--include-assurance` only。默认 Base 不安装该脚本。当用户要求评估 workflow 优化正 / 负收益，或需要复盘多个真实任务样本时，可在源仓或 assurance 安装上显式运行 `.agents/scripts/workflow-value-report.py --root . --format json`。它只聚合三文件、archive summary、run manifest、campaign metrics 和 skill curator report 的机制级信号；不读取业务源码树、raw logs、Graphify / CodeGraph 原始输出或 `$HOME/.codex`，不启动 reviewer / live eval / tools，不写状态，不进入 hooks / ship-check / closeout 默认链路。`keep / trial / downgrade-or-narrow / needs-data` 只是校准建议，不是交付 PASS、业务 ROI 证明或删除高价值 gate 的授权。
## Harness Repair Optimization Protocol
当真实项目暴露 workflow 缺陷、流程税、误触发、漏触发、重复返工或证据漂移时，优先修复现有 Harness，而不是新增 runner、memory runtime、默认多 agent 编队或第二状态源。本协议只用于 workflow-source 维护和显式 workflow 改进任务；普通 fast path / low 业务任务不因此升级。

触发条件：
- 同类问题在真实项目中重复出现，或单次问题达到 S1/S2，且能指向 workflow rule、validator、template、routing、skill trigger、archive / manifest、reviewer 或 closeout 机制。
- high / release / external-system 任务中出现证据缺口、reviewer 漏触发、waiver 漂移、release provenance 缺失、post-commit handoff 失真、archive / manifest 不可恢复等机制问题。
- 工作流源码本身发生较大改动，需要把修复方法、回归样例和验证路径固化。

标准流程：
1. Evidence intake：只收集最小可复核证据，优先使用三文件、archive `summary.md`、run `manifest.json`、validator output、git diff/status 摘要和 reviewer disposition；默认不加载 raw logs、全量 `.agent-state`、全量 `.agents/tasks` 或业务大文件。真实项目审计必须先做 Real Project Audit Epoch Preflight，确认样本是 legacy、migration 还是 current。
2. Attribution：先区分 `historical baggage / migration-window / execution-lapse / validator-gap / template-gap / routing-gap / review-gap / tooling-gap / flow-tax / external-change`。归因决定修复落点，不自动授权改文件；legacy / migration 样本不能直接升级成当前机制缺陷。
3. Independent challenge：S1/S2、workflow-source、high/release 机制变更或用户要求时，使用一个或多个只读视角做 challenge；它可以是子 agent、外部 reviewer 或本地 red-team，但不拥有状态源、不写文件、不替主 Codex裁决。
4. Repair existing harness first：优先修现有 reference、template、validator、eval、tooling-map 或 skill trigger；只有现有承载点不够且收益明确时才新增文件。不得因为一个缺陷就创建 runner、workflow state DB、root workflow JSON、自动 memory 或默认 live eval。
5. Positive / negative / boundary eval：validator 误报必须补 positive fixture；漏报必须补 negative / forbidden fixture；流程税问题必须补 no-trigger / not-needed fixture；所有 fixture 要有 failure oracle，避免只为单个项目样本过拟合。
6. Root state sync：workflow-source 复杂改动必须同步根 `task_plan.md`、`findings.md`、`progress.md`，记录范围、归因、修复文件、验证和剩余风险；不要把业务项目事实写进 starter 模板。
7. Validation ladder：按影响范围运行 py_compile / shell syntax、behavior eval、base smoke、workflow eval、相关 validator、full profile temp smoke（若影响 full profile）、`git diff --check`；不要用“模板看起来合理”替代验证。
8. Final review and closeout：S1/S2 或 workflow-source 机制改动收口前做独立复核或本地 S0/S1 red-team；修复 reviewer finding 后重新跑相关回归。最终只汇报改了什么、为什么、怎么验证、剩余风险。

裁决规则：
- `execution-lapse` 说明已有有效规则未被执行；除非重复且证据显示规则不清，否则不直接改 skill / template / reference，只记录提醒、common-pitfall、reviewer calibration 或 eval candidate。
- `historical baggage / legacy` 用 legacy-warn、migration report、archive summary 或 run manifest补强；不得让旧任务阻断当前 active work。
- `flow-tax` 先收窄触发条件、拆分 strict mode 或改为 report-only；不要删除高价值 gate。
- `validator false positive` 修复时必须保留一个应通过的 `positive fixture`；`validator false negative` 修复时必须保留一个应失败的 `negative fixture`。
- 多 agent 是 challenge / review 能力，不是必须的机械步骤；当它会拖慢低风险修复或缺少运行时能力时，用结构化本地 red-team 和 deterministic eval 替代。

边界：
- 本协议不是 `workflow-runner`、不是第二状态源、不是 backlog、不是自动 knowledge promotion、不是自动 eval generator。
- 任何派生报告、review packet、trace 或 campaign artifact 只能放在 `.agent-state/runs/<run_id>/...`，并标注 derived / reference-only。
- 修复结果要泛化到 starter-pack 的通用机制；不要把某个业务项目的路径、账号、部署状态或一次性调试结论写入模板。

## Workflow Evolution Evidence Chain
当一个 workflow-source 候选需要从 report 信号进入试点或决策时，使用可选 workflow-source appendix 和 `.agent-state/runs/<run_id>/harness-evolution/evolution-chain.json`。这条链只组织证据，不启动 agent、命令、eval 或变体，也不自动修改 workflow。

- `progress.md#Workflow Evolution Decision` 是 `adopt / rollback / reject / defer` 的唯一任务内决策记录；chain JSON 与 run manifest 都是派生证据。
- 候选 patch / config / rule artifact 必须放在 chain 的 `harness-evolution/` 目录，chain、progress decision 与所有 validation / pilot manifest 绑定同一个 `candidate_id / component_id / candidate_sha256 / task_epoch=current`。
- validation / pilot / rollback-check 不能只靠 argv 中出现候选路径；`capture-run-command.py` 还要求命令写出 `workflow-candidate-evaluation` JSON，并把 `candidate_result_ref / candidate_result_sha256` 写入 attribution。结果必须绑定候选 ID、候选摘要、phase、status 和 exit code。
- `adopt` 必须同时有 validation 和 pilot 通过证据；`rollback` 还必须引用结构化 adoption record、明确 rollback target 及其摘要，并让 rollback-check 绑定恢复目标；`reject` 需要失败/阻断验证；`defer` 不要求先运行候选。
- private held-out 仅允许 metadata ref 和稳定 sample-set digest，必须 explicit-run，不能存样本、答案或公开 benchmark 冒充 held-out；manifest 只声明来源类型，不证明来源已被独立验证。
- validator 只校验已有证据，不生成候选、不执行命令、不应用 patch、不进入 hooks、ship-check、fast path，也不在默认 CI 中自动发现或裁决业务候选。公开的 deterministic fixture 可以在 starter-pack CI 中回归 validator 契约，但不是业务 held-out 或自动进化运行。

### Harness Evolution Acceptance Contract

`validate-harness-experiment.py` and `validate-workflow-evolution.py` are source-assurance / `--include-assurance` only. Default Base 不安装这些脚本；只在 starter 源仓或 assurance 安装上做显式 workflow-source 实验时运行。

Evidence-chain completeness is not proof that a candidate improves the incumbent. For explicit workflow-source evolution decisions, validate an existing experiment with:

```text
.agents/scripts/validate-harness-experiment.py \
  --root . \
  --experiment .agent-state/runs/<run_id>/harness-evolution/experiment.json \
  --results .agent-state/runs/<run_id>/harness-evolution/acceptor-results.json \
  --format json
```

- The validator is a deterministic acceptance-contract checker for separately stored artifacts. It reads the proposer contract plus digest-bound result artifacts, recomputes row-level results, and emits `validation_status=pass/fail` plus `acceptance_status=trial-eligible/paired-evidence-complete/ineligible/inconclusive`; it never emits `adopt` or adoption eligibility.
- Artifact separation does not prove producer identity, truthful changed paths, acceptor-owned thresholds, process isolation, or OS-level isolation. The explicit external experiment must keep acceptor outputs, evaluator, oracle, task suite, and policy outside candidate write scope; the static report records `execution_isolation_verified=false` and `adoption_eligible=false`.
- `contract-only` is for bounded deterministic correctness/security repairs and requires positive, negative, boundary/no-trigger, regression, and anti-gaming evidence. It can only become `trial-eligible`.
- `paired` is for comparative quality, productivity, trigger, or default-behavior claims. Incumbent and candidate must use matching model, reasoning, toolchain, environment, budget, evaluator, oracle, and task-suite bindings. The validator ignores self-reported aggregate scores and recomputes target/no-trigger/regression counts from paired rows.
- Integrity, safety, retention, target evidence, no-trigger tax, and configuration lock are hard gates. A scalar score cannot offset a failed hard gate.
- Schema-v1 evolution chains remain readable only through explicit `--legacy-audit`, which returns an `audit-only` result that cannot serve as current adoption evidence. Schema v2 binds candidate, incumbent, and the acceptance report by path and sha256; `validate-workflow-evolution.py`（source-assurance / `--include-assurance` only）reruns the static contract checker and rejects stale or forged reports. Because independent execution is not yet verifiable, current schema-v2 `adopt` fails closed.
- `workflow-value-report.py keep` remains observational retention advice, not causal proof, adoption, starter-pack promotion, or business ROI.
- Real paired execution, private held-out samples, cross-project/OOD confirmation, repeated trials, sequential statistics, and shadow replay remain explicit external experiments. They are not supplied or run by this starter-pack validator.
- The acceptance contract does not join hooks, fast smoke, ship-check, task closeout, default business-task CI, or automatic project discovery. It cannot modify the candidate, evaluator, oracle, workflow, or task state.
## 单控制项成本实验与推广口径

本节只约束显式的 workflow-source 实验。它不是默认 CI、hook、任务状态、自动变体生成器或真实业务项目迁移授权。每一个候选只改变一个**逻辑控制项**；为实现同一控制项而必须联动的 manifest、renderer、fixture 和文档可放入同一个有界 candidate manifest，但不得顺带改变 reasoning、模型、工具、skill、MCP、reviewer、索引或任务集。

### 预注册最小字段

在运行前，候选的 `experiment.json` 或等价的测量结果必须声明：

- `candidate_id`、`component_id`、候选目的和单控制项边界；`component_id` 使用 Control Ledger 的 architecture 或 mechanism ID。
- `baseline_git_revision`、`candidate_git_revision`、`baseline_digest` 与 `candidate_digest`：对照和候选各自的不可变 commit 与有界 source/config manifest SHA-256，digest 不能相同。既有预注册不得用当前工作区改动刷新 candidate digest；新候选必须重新预注册。
- 固定的 `model.id`、`model.reasoning`、`model.config_digest`，以及 `environment.digest`、`environment.toolchain_digest`；模型或 CLI/工具变更即重新预注册。
- `outcome_grader.id` 和摘要；grader 要与候选写入面隔离。没有独立 grader 时只能记录 deterministic contract 结果，不能宣称生产力或质量提升。
- task class、target/no-trigger/regression route、重复次数、顺序/seed、timeout、预算和停损规则。
- token、wall、读取/工具、质量/返工、失败类别和 telemetry 覆盖范围。`measured`、`inferred`、`unavailable` 必须逐字段标注。

本轮四个 `WM-20260722-*` 候选的 digest-bound preregistration 位于仓库
`experiments/workflow-cost/modernization-controls/*.json`；可用
`python3 experiments/workflow-cost/verify-modernization-controls.py --format json`
复核。真实 measurement result 必须以 `experiment_contract.path` 和
`experiment_contract.sha256` 绑定其中一份控制项，不能只凭结果自身的字段
声称是单控制项实验。

推荐把派生输入和结果放在 `.agent-state/runs/<run_id>/harness-evolution/`。它们只绑定证据；不会应用候选、启动 agent、连接网络或升级任何 profile。

### 2026-07-22 预注册矩阵

| candidate_id | component_id | 唯一控制项 | task classes / required routes | 固定配置与重复 | outcome grader | 主指标与停损 |
|---|---|---|---|---|---|---|
| `WM-20260722-hook-narrowing` | `capability-execution` | 仅比较 lifecycle hook 事件/Stop dirty-fingerprint 策略；敏感命令 guard 保持不变 | fast no-trigger、standard target、high/release regression | 同一模型、reasoning、hooks digest、toolchain、seed；每 route 至少 4 个配对重复 | PTY/protocol + 允许时独立任务 oracle | token/wall、hook event、Stop 延迟、PTY/guard；任一 guard/阻塞回归立即停止并回退 |
| `WM-20260722-selector-contract` | `context-knowledge` | 仅比较 selector 的 Gate Card/预算路由，不改变代码定位器 | fast no-trigger、standard target、release negative wording | 同一模型、reasoning、reference/tool digest、任务文本与 seed；每 route 至少 4 个配对重复 | 明确路由/验收 oracle | 初始/阶段/累计上下文、误升级、首次定位/验证；出现风险字段误升/漏升即停止 |
| `WM-20260722-current-task-snapshot` | `lifecycle-recovery` | 仅比较共享只读 snapshot 与旧的重复解析 | fast no-trigger、standard active-state target、partial/conflict regression | 同一模型、reasoning、root-state fixture、工具链与 seed；每 route 至少 4 个配对重复 | snapshot + consumer compatibility oracle | 三文件读取次数/字节、wall、partial 行为、closeout 事实域；任一冲突被静默选取即停止 |
| `WM-20260722-skill-thinning` | `context-knowledge` | 仅比较 thin skill entry 与相同 Gate Card 的旧长正文 | fast no-trigger、focused target、assured regression | 同一模型、reasoning、skill/Gate Card digest、任务集与 seed；每 route 至少 4 个配对重复 | task acceptance + independent review where routed | 初始上下文、读取 token、漏触发/冲突、返工；任一必要安全卡未加载或 quality 退化即停止 |

“至少 4 次”是成本受控的试点下限，不是统计显著性证明。先跑 no-trigger 与安全/协议负例；出现两次同类不明失败、任何高风险 guard 退化、或 telemetry scope 不可信时停止余下重复并记录 `inconclusive`/`rollback`，而不是用平均值掩盖失败。

### 覆盖校验与禁止推断

显式结果可使用下列 report-only 检查（source-assurance / `--include-assurance` only；默认 Base 不安装该脚本）。它不会读取业务源码、执行实验、修改候选或给出 adoption 权限：

```bash
python3 .agents/scripts/workflow-value-report.py \
  --root . \
  --measurement-result .agent-state/runs/<run_id>/harness-evolution/measurement-result.json \
  --format json
```

结果至少含有 `measurement_coverage.token`、`wall_time`、`quality` 和逐 route 的 `outcome`、`safety`、`cost`。规则如下：

- `root-thread` usage 不得标成 `all-agent-total`；只有单 agent total 或 all-agent total 才能支持相应的 measured cost 口径。
- `estimated-bytes` 是 inferred 上下文代理，不能标成 measured token；没有官方/可观察 usage 时写 `unavailable`。
- 缺失 model config、environment、baseline/candidate digest、outcome grader、target/negative/regression route，或本轮 `WM-20260722-*` 的 preregistered control binding 时，结果被拒绝。
- 每条 route 的 `cost` 只能是 `improved`、`non-regression`、`regressed`、`inferred` 或 `unavailable`。若全部 route 已测得，`cost-improved` 必须至少有一条 target route 为 `improved`，且不得有 `regressed`；`non-regression` 也不得含 `regressed`。未测或 inferred 的成本只能使主张降为 `inconclusive`，不能用“未变差”冒充“已改善”。
- telemetry 缺失或 inferred 时，结构可有效但 `status=inconclusive`；它绝不能保留 `cost-improved` 主张。
- 通过覆盖检查只得到 `eligible-for-separate-decision`，不是 `adopt`、业务 ROI、profile 默认化或真实项目迁移授权。每条 route 都必须非退化；不能用跨 route 的全局平均抵消一个 no-trigger 或 regression 损失。

### Source-fixture 回归守卫（不等于真实任务实验）

可运行下面的 report-only 命令，基于 `5f2460a...` 基线 commit 与当前
starter-pack 的临时 overlay 比较 fast/focused/assured selector 样本、各 preset
hook 事件数，以及无 active root state 的 clean Stop 本地墙钟时间：

```bash
python3 experiments/workflow-cost/measure-modernization-source-fixtures.py \
  --repeats 12 \
  --format json
```

该报告明确把 selector 读取量标为 `inferred`、model token 和业务质量标为
`unavailable`，并固定 `promotion_status=inconclusive`。它可阻止 source-level
默认路径退化、帮助定位 hook 进程税，但不能作为任一候选的 adoption、真实 token
节省、返工下降或业务项目迁移证据。

### 决策记录和复验

每个候选在 `progress.md#Workflow Evolution Decision` 和 Control Ledger 的 owner 处记录 `adopt`、`narrow`、`retain-explicit-trial`、`rollback` 或 `reject`，并逐项写出：安全/quality outcome、成本分布、失败类别、soft scar、回退目标和下一次复验触发器。模型/reasoning、CLI/hook 协议、skill/Gate Card、工具 schema、环境镜像、任务分布或 telemetry 范围变化时，旧结果自动降为历史参考，重新做单控制项配对。

## Local Skill Promotion / Update Assessment
Local skill creation and update are assessment-gated, not automatic. The workflow may recommend local skill creation, update, or promotion; it must not create, update, promote, or install a skill automatically.

触发条件：
- `high` / `release` 任务使用了 repo-local skill。
- 重复 SOP、重复坑、稳定发布 / 部署流程或高风险 review 流程出现至少 2 次。
- 本轮修改 workflow、references、skills，或 ship-check / code_review 发现 skill 缺口。

决策值只用：
- `none`：没有 skill 沉淀价值。
- `candidate`：记录候选，继续观察。
- `update-needed`：现有 repo-local skill 需要更新，但不自动修改。
- `recommend-create`：建议新建 repo-local skill；这只是建议，不是执行许可。
- `recommend-promote`：建议从项目 skill 抽象到 starter-pack；这只是建议，不是执行许可。
- `defer`：有价值但证据不足、时机不合适或用户未授权。

禁止使用：`create-now`、`auto-create`、`auto-promote`、`self-update`。

边界：
- `recommend-create` / `recommend-promote` 不是授权；只有用户明确要求“创建 / 更新 / 推广这个 skill”，或任务本身明确要求“沉淀成 skill”，才可执行。
- Skill 不能自动修改自己；执行中发现缺口时，先写入 `findings.md` / `progress.md`，收口再评估。
- 项目事实变更时先更新 `.agents/references/`，再更新 skill 的引用或 SOP；references are source of truth, skills are SOP.
- `Local Skill Candidate Log` 只记录候选，不记录负责人、截止日期或状态流转；它不是 issue tracker 或第二套任务系统。
- `update-needed`、`recommend-create`、`recommend-promote` 必须先有调用证据、silent-bypass 检查、过拟合 / hardcoded literal 检查和 positive + negative trigger eval guard。缺少这些证据时只能写 `candidate` 或 `defer`。
- Silent-bypass 是独立风险：如果 skill 看起来正确但真实任务没有触发 / 没有被加载，不能声称 skill 有收益，也不能作为 promote 证据；应记录为 skill trigger / routing candidate。
- 创建或更新 skill 必须走 `$skill-creator`、`.agents/scripts/validate-local-skills.py`、workflow smoke / eval。

适合 skill 化：
- 高频重复出现，有明确触发词、稳定输入输出、固定步骤、验证标准和 forbidden actions。
- 能减少主会话重复解释，且不会创建第二套 plan / progress / handoff。
- 项目事实能通过 `.agents/references/` 引用，而不是复制进 skill。

不适合 skill 化：
- 单纯事实说明、当前状态、一次性事故复盘、尚未稳定的 workaround。
- 项目配置细节本身；这些应进入 `.agents/references/`。
- 会替代 `requirements-to-plan`、active three-file state contract、`ship-check` 或 `code_review.md` 的第二流程。

De-projectization Check：
- 从项目 skill 晋升到 starter-pack / global 前，必须移除项目名、路径、host、部署目标、账号环境和 kxslyy-only 假设。
- 项目事实改为参数或 references；保留正向和负向触发 case。
- 确认不默认 external-write、不读取 secrets、不创建第二状态源、不重复已有 starter-pack skill。
