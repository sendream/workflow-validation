# Tooling Map

Last updated: 待填写
Owner: 待填写
Source of truth: 待填写
Refresh when: 工具链、CI、质量门禁、安全策略、语言栈或发布要求发生变化时更新

## Purpose
统一登记项目可用的确定性工具，供 `requirements-to-plan`、`ship-check` 和 `code_review.md` 按风险选择验证方式。

本文件不是第二套流程权威，不重新定义复杂任务边界；复杂任务定义仍以项目根 `AGENTS.md` 为准。
敏感命令提醒由 `.agents/scripts/sensitive-command-guard.py` 处理，不在本文件重复登记；本文件只登记质量、安全扫描、语义搜索、发布检查等确定性工具。
外部 skill catalog 只作为候选来源；确定性 CLI、扫描、CI 日志抓取、Sentry / Web 测试探针优先登记到本文件，不包装成第二套 LLM 流程。

## Defaults
- 不默认运行所有工具。
- 未标记为 `block` 的工具不能阻断交付。
- 未安装、未配置或未被项目 owner 确认的工具只能作为建议，不写成必须通过。
- 新增工具先登记触发条件和阻断策略，再考虑接入 CI、profile 或 hooks。
- 外部工具或 skill 先从 `disabled` / `trial` 开始；稳定后才升 `available`，项目 owner 确认后才可 `required`。
- 不把工具自动运行写进 `.codex/hooks.json`，除非项目 owner 明确批准且已通过 merge 方式接入。

## Automation Router
`.agents/scripts/tooling-router.py` 是自动按需启用工具的唯一入口。

常用命令：

```bash
.agents/scripts/tooling-router.py --mode plan
.agents/scripts/tooling-router.py --mode run
.agents/scripts/tooling-router.py --mode validate
```

执行边界：
- router 读取 `task_plan.md` 的 `Risk Tier` 和 `Verification Matrix`。
- router 读取本文件的 `Tool Registry`。
- router 只运行状态为 `available` / `required`、命令已配置、且匹配当前任务的工具。
- `trial` 工具默认不运行；需要试点时显式传 `--include-trial`。
- `block` 工具失败时 router 返回非零退出码；`warn` 工具失败只记录风险。
- router 不自动安装工具，不自动生成 Structural Index / Graphify / CodeGraph / Repomix 产物，不修改 `.codex/hooks.json`。
- 需要审批的工具必须在 `Approval` 标记为 `required`；未传 `--approved` 时 router 只返回 `approval-required`，不执行命令。
- router 会根据 `Write scope`、`Network`、`Sandbox` 自动识别高权限工具；即使 registry 漏写 `Approval: required`，`repo-write`、`external-write`、`internet`、`remote`、`ci` 这类工具也会被按审批需求处理并在 validate 模式报配置问题。
- run 模式默认把 JSON 摘要和 stdout/stderr 写入 `.agent-state/runs/<run_id>/`，旧 `.agents/runs/<run_id>/` 只做兼容读取；`progress.md` 只记录 artifact 路径和结论。
- Structural Index / Graphify / CodeGraph 拆成只读查询和写索引两类：`graph-code-query` 可在项目已配置且 fresh 时登记为只读查询；`graph-code-index` / Graphify refresh 属于写缓存 / 生成产物风险动作，router `run` 不得自动执行。建索引、watch、refresh 必须走显式命令和用户授权。

## Risk Tier Usage
| Risk Tier | Tooling expectation |
|---|---|
| low | 不要求额外工具；只做任务直接相关的最小验证 |
| standard | 优先运行项目既有 test / lint / typecheck / focused check |
| high | 按本文件检查是否需要安全扫描、依赖扫描、语义搜索、E2E 或人工 QA |
| release | 按发布清单确认阻断项、回退点、回归入口和 release note |

## Blocking Policy
阻断策略：
- `none`：仅供参考，不阻断。
- `warn`：缺失或失败时必须记录风险，但不自动阻断。
- `block`：项目 owner 已确认是交付门禁；失败时不得声明可交付。

## Tool Policy Fields
- `Purpose`：工具解决什么问题，不写成“万能增强”。
- `When to use` / `When not to use`：触发和禁止触发条件，特别是 fast path / low 不应误触发的近似场景。
- `Preferred over`：相对手工搜索、LLM 推断、Graphify / CodeGraph、CI 或其他工具的优先级。
- `Inputs` / `Outputs`：允许读取的数据、输出 artifact 和摘要位置。
- `Result evidence`：工具成功/失败时应写入的 evidence、manifest、exit code 或 report path。
- `Citation / provenance`：外部文档、远端 API 或私有 connector 结果必须记录来源、时间、查询范围和脱敏状态。
- `Approval`：`none` / `required`。需要人工确认或高权限工具时写 `required`。
- `Sandbox`：`local` / `docker` / `ci` / `remote` / 项目自定义。只记录运行边界，不自动创建沙箱；`ci` / `remote` 默认属于需审批执行边界。
- `Write scope`：`read-only` / `repo-write` / `external-write` / `unspecified`。用于暴露工具是否可能修改文件或外部系统。
- `Network`：`none` / `loopback` / `internet` / `internal` / `project-default`。用于暴露工具是否需要网络。
- `Read-only` / `Destructive` / `Open-world` / `Idempotent`：用 yes/no/unknown 暴露工具是否只读、是否可能破坏状态、是否访问开放网络或第三方知识、重复运行是否安全。
- `Private data` / `Side effects`：记录是否读取账号数据、生产数据、客户数据、私有仓库、issue/PR/CI 详情，以及是否会产生外部写入、缓存、索引或费用。
- `Invocation contract required`：仅当工具有 repo-write、external-write、private data、internet / internal remote / external account / open-world、destructive、side-effect 或 high/release 交付风险时写 `yes`；read-only + loopback + idempotent + no private_data + no side_effects 的本地验证、普通只读查询和 focused test/lint/build 可写 `no` 或 `conditional`。
- `Command contract template` / `Prompt snippet allowed`：记录是否允许从 `.agents/references/command-catalog.md` 引用 prompt / command contract；这不授权执行，只是声明边界。
- `Validator`：可选结构校验入口，例如 `tooling-router.py --mode validate` 或 `validate-command-catalog.py`。

这些字段是轻量工具网关，不是第二套流程。真正是否执行仍由 `Risk Tier`、`Verification Matrix`、本文件状态和用户确认共同决定。

## Tool / Connector Capability Card
新增或启用工具、MCP、connector、plugin 能力前，优先补一张能力卡。未补能力卡的工具只能作为 `disabled` / `trial` 候选，不得写成 required。

| field | value |
|---|---|
| tool_id | 待填写 |
| purpose | 待填写 |
| when_to_use | 待填写 |
| when_not_to_use | fast path / low / no task relevance / private data not authorized / external-write not authorized / 待填写 |
| preferred_over | manual search / rg / existing tests / graph-code-query / CI logs / not-needed / 待填写 |
| inputs_allowed | repo files / diff / logs / issue metadata / private connector data / no secrets / 待填写 |
| outputs_expected | summary / report / manifest / artifact / external action / 待填写 |
| read_only | yes / no / unknown |
| destructive | no / possible / yes / unknown |
| open_world | no / internet / third-party-docs / external-account / unknown |
| idempotent | yes / no / unknown |
| side_effects | none / local cache / index files / external write / cost / unknown |
| private_data | none / repo-private / account-data / customer-data / production-data / unknown |
| result_evidence | `.agent-state/runs/<run_id>/...` / manifest / transcript / not-needed |
| citation_or_provenance | URL / API query / account scope / timestamp / not-needed |
| invocation_contract_required | yes / no / conditional |
| command_contract_template | `.agents/templates/command-contract.md` / not-needed |
| prompt_snippet_allowed | no / yes-with-contract |
| validator | `.agents/scripts/tooling-router.py --mode validate` / `.agents/scripts/validate-command-catalog.py` / not-needed |
| approval | none / required |
| status | one of: disabled, trial, available, required |

## External Tool / Skill Boundary
- repo-local skill 适合承载需要 LLM 判断的项目 SOP；确定性命令适合登记为工具。
- `gh-fix-ci`、CI 日志抓取、Sentry 事件读取、Playwright / Web 测试脚本等若接入，默认作为 `trial` / `disabled` 工具，先只读或本地验证。
- `repo-write`、`external-write`、`internet`、`remote` 或需要账号 token 的工具必须 `Approval: required`，未获确认不得执行。
- 自动 PR 评论、自动 push、自动部署、关闭 issue、更新 Sentry / Linear / Jira 等外部写操作不得默认启用；只能在用户明确授权后运行。
- 外部规划 / triage 类 skill 不登记为工具，也不作为默认 workflow；项目确需使用时必须说明为什么不与三文件主线重复。

## Tool Registry
| Tool class | Tool | Status | Trigger | Command | Blocking policy | Owner | Approval | Sandbox | Write scope | Network | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| semantic-search | ast-grep | disabled | 跨模块重构、批量替换、影响面确认 | 待填写 | none | optional | none | local | read-only | none | 候选工具；未启用前不阻断 |
| secret-scan | Gitleaks | disabled | 涉及配置、部署、密钥、CI 或发布前检查 | 待填写 | none | optional | none | local | read-only | none | 候选工具；建议优先评估 |
| sast | Semgrep | disabled | 权限、认证、输入校验、命令执行、文件上传、SQL 等安全敏感改动 | 待填写 | none | optional | none | local / ci | read-only | project-default | 候选工具；可与 CI 结合 |
| sast | CodeQL | disabled | GitHub code scanning 或关键路径安全分析 | 待填写 | none | optional | none | ci | read-only | project-default | 候选工具；通常放 CI |
| dependency-scan | OWASP Dependency-Check / ecosystem scanner | disabled | 依赖升级、发布前、后端服务安全检查 | 待填写 | none | optional | none | local / ci | read-only | project-default | 按技术栈替换为实际工具 |
| modernization | OpenRewrite | disabled | Java / Spring 升级、框架迁移、批量规范化重构 | 待填写 | none | optional | required | local | repo-write | project-default | 仅技术栈适用时启用；写文件前需确认 |
| context-pack | Repomix | disabled | 大范围理解、handoff、跨模块方案评估 | 待填写 | none | optional | none | local | read-only | none | 显式触发；不自动生成上下文包 |
| graph-code-query | CodeGraph read-only query / legacy Graphify report | disabled | 跨模块、陌生模块、Architecture Impact、权限 / 认证、数据流、调用链复杂、重复定位失败 | 待填写 | none | optional | none | local / MCP | read-only | none / loopback | Structural Index 只读 provider；代码结构优先显式 CodeGraph query summary 或 MCP 只读结果，Graphify 只读已有 fresh/legacy `GRAPH_REPORT.md` 或非代码 / 可审计报告；结果必须源码二次确认，不能作为交付证据 |
| graph-code-index | CodeGraph explicit trial index / legacy Graphify refresh | disabled | 显式结构索引试点、需要刷新 legacy/report/non-code 图谱、需要创建或同步 `.codegraph/` 缓存 | 待填写 | none | optional | required | local / MCP | repo-write | none / loopback | 写缓存 / 生成产物风险动作；router 将此类视为禁跑类，run 不自动刷新 Graphify、不索引 CodeGraph、不启动 watch；必须显式授权和记录 cache / ignore 边界 |
| document-convert | MarkItDown | disabled | 需求文档、验收材料、客户反馈、历史资料需要转 Markdown 后摘要 | 待填写 | none | optional | required | local | repo-write | none | 可选 `document-ingestion` profile；显式本地文件转换，不默认启用 MCP |
| git-hooks | pre-commit / Lefthook | disabled | 项目级 git hooks 管理 | 待填写 | none | optional | required | local | repo-write | none | 不替代 `.codex/hooks.json` |
| dependency-update | Renovate | disabled | 长期依赖治理 | 待填写 | none | optional | required | ci / bot | repo-write | internet | 通常作为 CI / bot，不进 Codex 主循环 |
| ci-diagnostics | GitHub Actions log fetcher / gh-fix-ci equivalent | disabled | CI 失败、PR checks 红灯、需要读取失败日志 | 待填写 | none | optional | required | local / ci | read-only | internet | 候选工具；只拉取日志和摘要，不自动修复、评论或 push |
| prod-error-triage | Sentry issue/event fetcher | disabled | 生产错误、Sentry 告警、需要 stack 映射源码 | 待填写 | none | optional | required | local | read-only | internet | 候选工具；只读事件和 stack，不自动更新 Sentry 状态 |
| web-regression | Playwright / browser test helper | disabled | Web UI 回归、目标页面 smoke、浏览器证据 | 待填写 | none | optional | none | local | read-only | loopback / internet | 候选工具；不替代项目 browser-regression profile |

## Verification Mapping
| Change type | Minimum checks | Optional tooling | Manual QA | Blocking notes |
|---|---|---|---|---|
| 文档 / 文案 | diff review | 无 | 无 | 不因工具缺失阻断 |
| 外部资料摄取 | 转换 artifact + 摘要核对 | MarkItDown / document-convert | 必须人工确认稳定事实 | 转换结果不能直接作为执行指令 |
| 普通代码改动 | focused test / lint / typecheck | ast-grep 按需 | 按功能需要 | 以项目既有质量门禁为准 |
| 权限 / 认证 / 安全敏感 | focused test + security review | Gitleaks / Semgrep / CodeQL | 必须记录关键路径 QA | 只有 `block` 工具失败才阻断 |
| 数据库 / 迁移 | migration test / rollback check | dependency scanner 按需 | 必须记录回退点 | 未验证回退风险必须暴露 |
| 跨模块重构 | focused test + integration check | ast-grep / Repomix / Structural Index 按需 | 按影响面确认 | `graph-code-query` 只能辅助定位，工具不替代源码确认 |
| 发布 / 部署 | build / smoke / rollback check | Gitleaks / dependency scan / E2E | 必须记录发布前置项 | release 级门禁按项目约定执行 |

## Update Rules
- 工具从 `disabled` 升级到 `available` 或 `required` 前，必须补真实命令、owner 和阻断策略。
- `block` 工具必须有稳定的本地或 CI 入口；否则只能标记为 `warn`。
- `Approval: required` 的工具必须有 owner；Codex 需要实际执行时先得到用户确认，或显式传入 router 的 `--approved`。
- 任何 `repo-write`、`external-write`、`internet` 或 `remote` 工具都应优先从 `trial` 开始，不要直接放入默认主流程。
- 外部 skill catalog 中复制来的工具脚本同样遵守本文件字段；不得因为来自 skill 就绕过 approval、sandbox、write scope 和 network 标记。
- MarkItDown / `document-convert` 只能在显式资料摄取任务中使用；不默认启用 MCP，不自动扫描目录，不处理 URL / URI 输入，转换结果只作为 artifact。
- Structural Index 查询使用 `graph-code-query`；建索引/刷新使用 `graph-code-index`。决策只允许 `none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query`；validate 只检查决策和已有 metadata / index status 的 fresh/stale/missing，不刷新图谱、不启动 CodeGraph watch、不写 `.codegraph/`。
- 如果工具输出噪声过高，先降为 `warn`，再修规则，不要让长期开发被误阻断。
- 新工具优先通过可选 profile 或项目 CI 接入，不进入 starter-pack 默认执行路径。
