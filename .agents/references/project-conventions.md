# Project Conventions

Last updated: 2026-08-23
Owner: Black maintainers
Source of truth: `pyproject.toml`, `docs/contributing/the_basics.md`, `docs/the_black_code_style/index.md`, `docs/the_black_code_style/future_style.md`
Refresh when: 工具链、目录结构、发布方式、评审规则或工程约定发生变化时更新

> 只写稳定、长期有效、团队认可的项目约定。不要写一次性任务状态。

## Project boundary
- 仓库用途：Black Python 代码格式化器的源码、测试、文档与发布配置
- 主要交付物：`black` Python package、CLI、`blackd` 与编辑器 / 工具集成
- 不在本仓库处理的内容：下游项目的格式化策略与项目私有配置

## Package manager
- Preferred: 项目外部 Python virtual environment + `pip`
- Do not use: 向系统 Python 安装本仓开发依赖
- Dependency version policy: exact pin / compatible range + committed lockfile / 项目约定（待填写）
- Install / lifecycle scripts: 支持默认禁用的生态应默认禁用或逐包审查；例外记录精确 `package@version`、原因与复核入口

## Build
- Main build command: `pip install -e ".[d]"`
- Service-specific build commands: 待填写

## Test
- Main test command: `env -u NO_COLOR python -m pytest -n auto`
- Focused test command: `env -u NO_COLOR python -m pytest tests/test_black.py`
- E2E command: not-needed
- Environment requirement: Black tests must run with `NO_COLOR` unset. `src/black/output.py` intentionally honors the standard `NO_COLOR` variable, while `test_piping_diff_with_color` and `test_expression_diff_with_color` at baseline `8947c48e` do not isolate it; all trial acceptance runs therefore use `env -u NO_COLOR` unless a test explicitly covers `NO_COLOR` behavior.

> full trajectory monitor 只把上述 Build / Test 字段中的单个反引号 code span 当作可选命令前缀，例如 `pytest -q`；不填写不会阻断，含控制符、多命令、换行或占位符的值不会被采信。

## Quality gates
- Lint: 待填写
- Typecheck: 待填写
- Format: 待填写
- Tooling map: `.agents/references/tooling-map.md`
- Tooling router: `.agents/scripts/tooling-router.py`
- Verification Matrix: 复杂任务在 `task_plan.md` 按 `Risk Tier` 填写，不默认运行所有工具

## Environment / path policy
- Primary execution environment: Linux
- WSL project path: 待填写
- Windows project path: 待填写
- Path conversion: 需要跨 WSL / Windows 时显式使用 `wslpath` 或项目约定脚本；不要依赖 hook 自动改写
- Shell scripts: 在 WSL shell 中使用 `/mnt/<drive>/...` 或 Linux 路径，禁止硬编码 `C:\...`
- Windows program calls: 只有调用 `explorer.exe`、PowerShell、Windows Chrome 或 Windows 原生命令参数时才使用 Windows 路径
- Browser regression: 如果启用，固定到 `.agents/references/browser-regression.md`
- Known-bad path guard: `NO_COLOR=1 python -m pytest -n auto` fails the two with-color tests at baseline `8947c48e`; use `env -u NO_COLOR python -m pytest -n auto`. Re-test the known-bad path only when those tests gain explicit environment isolation or color-environment handling changes.
- Environment debt gate: 登记已知坏环境和稳定 workaround；生产开发 / 发布交付阶段默认走稳定路径，只有环境修复任务、稳定路径失效或用户明确要求时才重试坏环境

## Stable execution matrix
> 用来沉淀跨 WSL / Windows / Linux 的稳定执行入口。不要把一次性成功命令写成长期事实；只有重复使用或 release 级验证过的入口才填入。

| task class | preferred side / command | known-bad side / command | when to re-test known-bad path |
|---|---|---|---|
| Java / Maven | 待填写，例如 Windows `mvn.cmd` + 明确 JDK / Linux Maven | 待填写，例如 WSL 缺 Java / Maven 或 PowerShell `-D` 参数解析问题 | 环境修复任务、稳定路径失效、JDK/Maven 版本变化 |
| frontend with existing `node_modules` | 待填写，例如 Windows `pnpm.cmd` 或 WSL `pnpm`，以依赖目录实际形态为准 | 待填写，例如复用另一侧 native/symlink 依赖 | 重新安装依赖、锁文件变化、运行侧切换 |
| SSH / deploy / remote smoke | 待填写，例如 WSL OpenSSH（若已验证稳定）、Windows OpenSSH + PowerShell 参数数组、Linux OpenSSH | 待填写，例如未修复的 WSL OpenSSH 卡住、scp quoting 失败、跨 shell inline quoting 失败 | 用户要求修 SSH、稳定路径失效、需要验证坏路径已修复或确认修复仍有效 |
| browser / CDP | 待填写，例如 Windows Chrome CDP / Linux browser | 待填写，例如 WSL 缺 Chrome 分发版 | 浏览器安装变化、回归工具升级 |
| HTTP smoke | 待填写，例如 `curl --max-time` / 带 timeout 的脚本 | 无 timeout 的 fetch / grep / remote wait | 仅在超时策略变化时 |

## Architecture conventions
- Layering: 待填写
- Dependency direction: 待填写
- Error handling style: 待填写
- State management style: 待填写
- API client pattern: 待填写
- Data access pattern: 待填写

## Change rules
- When behavior changes: Add the corresponding entry under the appropriate `CHANGES.md` heading; omission requires the project maintainer's explicit `ci: skip news` disposition.
- When API changes: 待填写
- When schema changes: 待填写
- When config changes: 待填写
- Formatting stability: Most style changes must first enter `--preview`; crash fixes and changes that do not alter already-formatted files may bypass preview. Preview features are expected to reach the next stable style; features with known blocking issues belong in `--unstable` and stabilize only after those issues are fixed.

## Field contract / nullability policy
- Cross-layer field contract owner: 待填写
- Empty value strategy: 待填写，例如业务允许空值但数据库 `NOT NULL` 时，后端必须统一归一化为项目约定值
- Applies to entry points: registration / reset / save / import-export / 待填写
- Backward compatibility: 待填写
- Refresh when: 字段校验、数据库 nullability、导入导出格式或入口列表变化时更新

## Sensitive operation policy
- Strict guard: disabled / enabled
- Strict flag: `.agent-state/flags/sensitive-guard-strict.enabled` 或 `CODEX_SENSITIVE_GUARD_STRICT=1`
- Requires explicit confirmation: `.env`、`.ssh`、私钥、证书、token、sudo、数据库写入、生产部署、批量删除、权限变更、force push
- Required preflight: 命令意图、影响范围、验证方式、回退点
- Required record: `progress.md` 的 `Sensitive Operations`

## Delivery rules
- 是否允许直接改主分支：待填写
- 是否允许创建 worktree：待填写
- 是否需要用户确认后再做的大动作：待填写

## Source Root Registry
> 稳定 source-root 注册表，只记录长期项目边界；不是当前任务状态源。当前任务实际碰到哪些 root，写 `progress.md#Source Roots / Repos Touched`。多 git root、项目根不是 git root、release/external-system、Structural Index 查询或 CodeGraph 试点时优先维护本表。
> `source_root` 应是最小真实源码根；不要指向 `.agent-state/`、`.agents/tasks/`、Graphify / CodeGraph 输出、依赖、构建产物、缓存、日志、归档或运行数据。单仓项目可用 `.`，但必须确认 `.gitignore` / ignore 边界排除了生成物和运行数据。

| root_id | repo_id | vcs_root | source_root | language / runtime | build target | test target | owner | evidence_scope | release_artifact_scope | structural_index_provider | status | refresh_when |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| not-needed / backend | repo / not-needed | `.` / `backend` / not-needed | `src` / `backend` / not-needed | Java / Node / Python / mixed / 待填写 | not-needed / 待填写 | not-needed / 待填写 | 待填写 | run-manifest / release-source / source-file / not-needed | none / jar / dist / container / package / not-needed | none / graphify / codegraph / both | active / disabled / legacy / not-needed | source root moved; build/test target changed; index provider changed; release scope changed |

## Structural Index policy
- Provider: none / graphify / codegraph / both
- Provider rule: 默认 `none`；每个 source root 优先只选一个 provider。代码结构定位优先考虑 CodeGraph 显式只读查询 / 试点；Graphify 主要保留为 legacy/fresh 报告读取、可审计结构报告、非代码语料或跨文档知识图谱。`both` 只在任务同时需要 Graphify 报告 / 非代码图谱和 CodeGraph 实时调用链 / impact 查询时使用。
- 状态：disabled / missing / enabled-fresh / enabled-stale / trial
- Status rule: `trial` 是状态，不是 provider；CodeGraph 试点必须同时记录 provider、scope、metadata、cache / ignore 边界和授权来源。
- 当前状态：disabled
- 是否提交 `graphify-out/` / `.codegraph/` / `codegraph-out/`：默认否；这些是本地派生物或缓存，不进入业务 Git / 交付包
- 是否提交原始图数据：默认否；业务子仓库应忽略 `src/graphify-out/`、`.codegraph/`、`codegraph-out/` 或等效结构索引输出目录
- Structural index owner：待填写
- Source roots：以 `Source Root Registry.root_id/source_root` 为准；Structural Index 查询必须绑定 `root_id`，禁止直接扫 `.agent-state`、`.agents/tasks`、Graphify / CodeGraph 输出、依赖、构建产物、缓存、日志、归档或运行数据
- Graphify 生成入口：`.agents/scripts/graphify-refresh.sh --dry-run <source-root> [...]`，确认后再运行 `.agents/scripts/graphify-refresh.sh --yes <source-root> [...]`；新代码任务不要把 Graphify refresh 当作默认补图路径
- CodeGraph 入口：待填写；代码结构查询优先使用显式只读 CodeGraph query / MCP result；只能作为项目级显式试点或已配置 MCP 只读工具使用，禁止默认全局安装、自动 watch 或自动修改 hooks / 三文件
- CodeGraph trial metadata path：not-needed / 待填写；必须位于 `.agent-state/runs/<run_id>/...` 或项目显式允许的本地派生 cache，不得成为状态源
- CodeGraph per-root freshness：每个 `root_id` 单独记录 `fresh / stale / missing / unknown / trial`、metadata path、query time、source snapshot；不要用一个项目级 freshness 代表所有 source root
- CodeGraph freshness rule：not-needed / 待填写；默认只信显式查询或试点 metadata，不从默认 hook 推断 freshness。空结果、stale root、`reindexRecommended=yes` 或 index-only confidence 只能缩小候选阅读范围，不能缩小验证范围、不能作为 PASS / release evidence，也不授权自动 reindex/watch/refresh
- Decision modes：`none / query-existing / refresh-dry-run / trial-index-codegraph / refresh-and-query`；默认 `none`，代码结构优先 CodeGraph `query-existing`；Graphify 刷新用 `refresh-and-query`，CodeGraph 建索引用 `trial-index-codegraph`，二者都必须显式授权
- Last generated：无 / 待填写
- Source snapshot：由 `graphify-refresh.sh --yes` 写入 `graphify-out/REFRESH_METADATA.md`；stale checker 优先按 snapshot 判断，旧 metadata 才 fallback 到文件 mtime
- 稳态升级方向：当项目愿意承担额外成本时，优先用 git commit/tree hash 或 source content hash 替代 mtime；未明确评估前不自动启用
- 何时必须重建图谱 / 索引：待填写
- stale 提醒入口：`.agents/scripts/graphify-stale-check.sh --mark --quiet` 只写 `.agent-state/flags/graphify-stale.flag`，不生成图谱；旧 `.agents/state/graphify-stale.flag` 只做兼容读取
- `.graphifyignore` / CodeGraph ignore 维护原则：排除依赖、构建产物、缓存、日志、归档、临时状态、敏感配置、`graphify-out/`、`.codegraph/` 和 `codegraph-out/`
- hooks 规则：不把 Graphify 自动刷新或 CodeGraph 自动建索引 / watch 写入 `.codex/hooks.json`

## Review expectations
- Minimum verification: `env -u NO_COLOR python -m pytest -n auto`
- Required docs updates: User-visible changes require the appropriate `CHANGES.md` entry; advertised code-style changes also update the code-style docs, with preview changes documented in Future Style.
- Required tests updates: Bug fixes and new features require a regression test; run it RED before the implementation and GREEN afterward.
- Tool-assisted checks: 以 `.agents/references/tooling-map.md` 为准；只有标记为 `block` 的工具失败才阻断交付
- Pattern escalation: 同构模块或同一缺陷家族出现第 2 个时，按 `workflow/lifecycle-recovery.md` 记录 sibling audit 结论
- Dependency/browser patches: 第三方 UI / DOM / 浏览器自动化 workaround 需按 `workflow/tooling-safety.md` 先完成最小复现、官方 / 版本 / 配置确认和 wrapper / adapter 评估
- Push Gate: Codex 被要求 push 前必须完成本地 Red-team checklist 和敏感操作检查；是否启用 git pre-push hook 由项目 owner 单独决定

## Forbidden shortcuts
- Shortcut 1: 待填写
- Shortcut 2: 待填写
- Shortcut 3: 待填写
- Shortcut 4: 待填写；建议登记“已知坏路径 + 稳定替代方案存在时，仍在交付任务中默认重试坏路径”
- Shortcut 5: 待填写；建议登记“未确认根因就直接 patch 第三方 UI / DOM / 浏览器自动化依赖”
