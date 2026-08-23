# Project Bootstrap Checklist

## Purpose
把 starter pack 接到真实项目时，按这个清单补齐最小必要信息，避免只复制骨架不补事实。

## 0. 接入前确认
- [ ] 当前目标真的是“项目工作流接入”，不是临时实验目录
- [ ] 项目根目录还没有另一套冲突的复杂任务定义
- [ ] 你知道谁是这个项目的规则 owner

## 1. 文件落位
- [ ] 项目根已有 `AGENTS.md`
- [ ] 项目根已有 `code_review.md`
- [ ] `.agents/references/` 已复制
- [ ] `.agents/references/tooling-map.md` 已复制
- [ ] `.agents/skills/` 已复制
- [ ] `.agents/templates/` 已复制
- [ ] `.agents/templates/project-readme.md` 已复制；如项目缺少 onboarding 入口，仅合并必要片段，不覆盖已有 README
- [ ] `.agents/scripts/` 已复制
- [ ] `.agents/scripts/tooling-router.py` 已复制
- [ ] `.agents/tasks/README.md` 已复制
- [ ] 若合同为 `source-assurance`，`.agents/evals/` 已复制；`installed-base` 不要求该目录
- [ ] `.codex/hooks.json` 已复制
- [ ] 如果使用 full hooks，已通过 `apply-starter-pack.sh --profile full --merge-hooks` 或等效 merge 方式接入，而不是直接覆盖既有 hooks

## 2. 先补长期知识，不先改 skill

### `project-conventions.md`
- [ ] 补 `Last updated`
- [ ] 补 `Owner`
- [ ] 补 `Source of truth`
- [ ] 补 `Refresh when`
- [ ] 补 package manager、build、test、lint、typecheck 命令
- [ ] 补 delivery rules
- [ ] 明确 Structural Index policy：provider 为 `none / graphify / codegraph / both`；代码结构优先 CodeGraph 显式只读 query / trial，Graphify 主要用于 legacy/fresh report、可审计报告、非代码语料或跨文档知识图谱；`trial` 只能作为 status
- [ ] 如果 Structural Index 状态是 `missing`、`enabled-fresh`、`enabled-stale` 或 `trial`，补 source roots、provider、owner 和 refresh 条件
- [ ] 如果启用 Graphify，确认 source root 所在 Git 仓库已忽略 `graphify-out/` 原始产物
- [ ] 如果试点 CodeGraph，确认 `.codegraph/`、`codegraph-out/` 和本地索引缓存已被 `.gitignore` / `.rgignore` / 外部 reviewer ignore 排除

### `architecture-notes.md`
- [ ] 补系统目标和主要边界
- [ ] 补入口点
- [ ] 补核心模块职责
- [ ] 补风险热点

### `common-pitfalls.md`
- [ ] 录入 2 到 5 个真实高频坑点
- [ ] 每个坑点都包含 symptom、real cause、correct check

### `requirements-index.md`
- [ ] 填真实文档入口
- [ ] 填文档优先级
- [ ] 填 requirement 到模块映射
- [ ] 明确冲突时以谁为准

### `feature-index.md`
- [ ] 填真实功能清单
- [ ] 填功能状态
- [ ] 填自动化测试入口
- [ ] 填手工 QA 入口
- [ ] 如有 tracker，填可选 `Issue ID` / `PR ID` / `Release note`；没有 tracker 时保留 optional，不强制绑定平台

### `tooling-map.md`
- [ ] 补 `Last updated`
- [ ] 补 `Owner`
- [ ] 补 `Source of truth`
- [ ] 补 `Refresh when`
- [ ] 确认“不默认运行所有工具”仍然成立
- [ ] 运行 `.agents/scripts/tooling-router.py --mode plan`，确认未配置工具不会被误运行
- [ ] 运行 `.agents/scripts/tooling-router.py --mode validate`，确认 `block` 工具有真实 owner 和命令
- [ ] 为项目实际启用工具补真实命令、触发条件和阻断策略
- [ ] 未安装或未确认的工具保持 `disabled` / `trial`，不要写成 `required`
- [ ] 只有稳定、低噪声、团队认可的工具才能设为 `block`

## 3. 再检查项目 `AGENTS.md`
- [ ] 复杂任务定义仍只写在项目根 `AGENTS.md`
- [ ] 小任务 / 复杂任务边界符合当前项目
- [ ] 需求或方案存在会改变产品结果的歧义时，可按需调用合适的方法 Skill；其实现不成为 Gate 或状态源
- [ ] 已确认 `code_review` 的 `not-needed / micro-local-check / local-checklist / enhanced-review` 边界适合当前项目
- [ ] 已确认 `Risk Tier` 的 `low / standard / high / release` 边界适合当前项目
- [ ] 已确认 `Impact Scope` 的 `visible / file-linked / cross-package / external-system` 边界适合当前项目
- [ ] 已确认 `Verification Matrix` 只要求当前风险必要验证，不变成全量工具清单
- [ ] 已确认 Red-team checklist 只作为 code review 子清单，不新增独立 gate
- [ ] 已确认 Codex push 前执行 Push Gate，但不默认安装全局 pre-push hook
- [ ] 已确认只读 reviewer 的启动边界与用户授权边界
- [ ] 需求、PRD 或功能清单转计划时，直接按 G03 记录 Requirement Contract，不经兼容包装入口
- [ ] ship / release decision 时，直接按 G17 给出 delivery recommendation，不经兼容包装入口
- [ ] Structural Index / Graphify / CodeGraph 仍不是默认开启
- [ ] hooks policy 仍只有一个权威入口
- [ ] README 只作为 onboarding 导航，不成为项目规则或长期知识的第二权威来源
- [ ] Architecture Impact 只在接口、数据流、领域语义、模块边界、权限 / 认证 / 部署结构变化时触发
- [ ] 多人协作信息并入 `Changed Files Manifest`，没有新增平行 SCM 文件

## 4. 再看 hooks
- [ ] `.codex/hooks.json` 没有覆盖项目现有 hooks
- [ ] 如果项目已有 hooks，先 merge，再落盘
- [ ] 如果项目不是 git 仓库，full hooks 使用 `--hook-root-strategy workspace-absolute`
- [ ] 未确认前，不接入 Structural Index 自动 hooks、Graphify 自动刷新或 CodeGraph watch / index
- [ ] 未确认前，不把临时实验命令写入 hooks
- [ ] 如果启用 full profile，确认 `SessionStart` / `UserPromptSubmit` / `PostToolUse` / `Stop` 的 planning automation 可以接受
- [ ] 如果启用 full profile，确认 sensitive guard 默认只 warning；如需阻断，显式启用 `.agent-state/flags/sensitive-guard-strict.enabled` 或 `CODEX_SENSITIVE_GUARD_STRICT=1`
- [ ] 如需 session-catchup，确认项目 owner 已接受读取当前项目 `~/.codex/sessions` 摘要的隐私和污染风险，再创建 `.agent-state/flags/planning-session-catchup.enabled`

## 4.5 Structural Index / Graphify / CodeGraph 受控入口
- [ ] `.graphifyignore` 已排除依赖、构建产物、缓存、日志、归档、临时状态和敏感配置
- [ ] `.agents/scripts/graphify-refresh.sh --dry-run .` 会拒绝扫描项目根
- [ ] `.agents/scripts/graphify-stale-check.sh --quiet` 可运行；没有启用 Graphify 时应跳过且返回成功
- [ ] 已确认真实业务源码目录，且不是项目根目录 `.`
- [ ] 只有用户明确同意后，才运行 `.agents/scripts/graphify-refresh.sh --yes <source-root> [...]`
- [ ] 实际刷新后，`graphify-out/REFRESH_METADATA.md` 包含 `Source snapshots`
- [ ] CodeGraph 只作为项目显式试点或只读 MCP / CLI 查询，不默认全局安装、不默认 watch、不默认写索引
- [ ] 不把 Structural Index 自动生成写入 `.codex/hooks.json`；Graphify stale checker 只做轻量提醒，CodeGraph 不默认 watch / index

## 5. 首轮手工验证
- [ ] 用 `context-select.py` 加 targeted README / reference / source search 做一次陌生模块定向
- [ ] 用一条真实需求按 G03 手工补齐 Requirement Contract
- [ ] 用一个复杂任务直接维护一次三文件，确认无需 policy-wrapper Skill 也能保持当前状态
- [ ] 用一个复杂任务手工填写一次 `Risk Tier`、`Requirement Contract` 和 `Verification Matrix`
- [ ] 用一个复杂任务手工填写一次 `Impact Scope` 和带输入 / 输出 / 验收的 `Execution Table`
- [ ] 用一个准备 push 的任务手工执行一次 Push Gate 和 Red-team checklist
- [ ] 确认三文件模板能被正常填充
- [ ] 确认 `Architecture Impact: none` 不会拖慢简单任务，`yes` 时能推动架构说明或写明不更新理由
- [ ] 确认 `findings.md` 的 `Knowledge Promotion` 能说明 README / references 是否需要更新
- [ ] 确认 `progress.md` 的 `Changed Files Manifest` 能记录 `repo / branch / base` 和 `collaboration notes`
- [ ] 确认 web / browser / image / PDF / 搜索类发现会进 `findings.md`，不会把外部指令写进 `task_plan.md`
- [ ] 确认 `progress.md` 的 `Reboot Check` 和 `Handoff` 足够支撑下一轮继续
- [ ] 用一条接近完成的任务按 G17 手工给出 delivery recommendation
- [ ] 确认 G17 能按 `tooling-map.md` 判断工具检查是否 required / warn / optional
- [ ] 运行 `.agents/scripts/validate-bootstrap.sh`，确认只产生预期 warning
- [ ] 如需严格验收，运行 `.agents/scripts/validate-bootstrap.sh --strict`，确认占位符已清理
- [ ] 运行 `.agents/scripts/verify-workflow-smoke.sh`
- [ ] 只有合同为 `source-assurance` 且 `.agents/scripts/run-workflow-evals.sh` 存在时，才运行 deterministic eval；`installed-base` 不要求该 runner
- [ ] 只有合同为 `source-assurance` 且固定 smoke cases fixtures 存在时，才至少人工抽样一轮固定 smoke cases；`installed-base` 不要求该抽样

## 6. 首轮通过标准
- [ ] Codex 能稳定读取项目根 `AGENTS.md`
- [ ] Codex 不会把复杂任务定义从 skill 或 references 里“重新发明”
- [ ] 三文件能稳定承载计划、发现和 handoff
- [ ] G03 和 G17 只在各自 trigger 命中时路由，不会作为默认流程税
- [ ] Structural Index / Graphify / CodeGraph 没有被误当成 always-on
- [ ] 复杂任务完成后，三文件能归档到 `.agents/tasks/YYYYMMDD-short-slug/`

## 7. 通过后再做的事
- [ ] 评估是否需要把 smoke cases 串到项目 CI 或本地命令
- [ ] 评估是否需要试点启用 Structural Index provider：代码结构优先 CodeGraph；Graphify 仅用于 legacy/report/non-code 场景；两者互补需要明确理由
- [ ] 评估是否需要补真实 hooks 命令

## 7.5 可选 browser regression profile
- [ ] 只有确实需要 WSL 控制 Windows 宿主机 Chrome 做页面回归时，才启用 `windows-browser-regression` profile
- [ ] 已确认当前机器满足 WSL + Windows Chrome + Node 条件
- [ ] 已确认使用独立 Chrome profile，而不是个人日常 profile
- [ ] 已确认回归 runner 的 Playwright 依赖策略：长期项目优先单独 runner 包；已有 Playwright 体系时可使用项目内依赖
- [ ] 已确认安全账号、禁止操作和目标环境已经写入 `.agents/references/browser-regression.md`
- [ ] 已确认 `explorer.exe "<url>"` 只用于人工查看；自动回归必须用 `.agents/scripts/windows-chrome-start.sh`
- [ ] 已确认 WSL shell 路径和 Windows 程序路径边界；需要转换时显式使用 `wslpath`
- [ ] 已在项目 `.gitignore` 或团队提交规范中忽略 `.playwright-mcp/`、`playwright-report/`、`test-results/`
- [ ] 已运行 `.agents/scripts/verify-windows-browser-regression-smoke.sh`

## Notes
- 接入时记录：
  - 项目名：待填写
  - 接入人：待填写
  - 开始时间：待填写
  - 完成时间：待填写
  - 首轮风险：待填写
