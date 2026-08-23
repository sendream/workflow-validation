# Project README

> 这是可合并到真实项目根 `README.md` 的 onboarding 片段。不要直接覆盖已有 README；只在项目缺少“新会话/新人接手入口”时合并必要部分。

## Project Overview
- 项目名称：待填写
- 项目用途：待填写
- 主要交付物：待填写
- 当前维护 owner：待填写

## Start Here
1. 先读项目根 `AGENTS.md`，确认本项目的复杂任务定义和边界。
2. 再读 `.agents/references/project-conventions.md`，确认项目约定、真实源码目录和验证命令。
3. 如果是继续未完成任务，先读 `progress.md` 的 `Handoff`。
4. 如果 `progress.md` 显示上一任务已完成但未归档，先按 `.agents/tasks/README.md` 归档或确认继续。

## Repository Boundaries
- 项目根目录：待填写
- 真实业务代码目录：待填写
- 只读参考目录：待填写
- 不应由 Codex 默认修改的目录：待填写

## Common Commands
| purpose | command | notes |
|---|---|---|
| install | 待填写 | 待填写 |
| build | 待填写 | 待填写 |
| test | 待填写 | 待填写 |
| lint | 待填写 | 待填写 |
| typecheck | 待填写 | 待填写 |
| start dev | 待填写 | 待填写 |

## Workflow Entry
- 简单任务：走 fast path，最小改动 + 最小验证。
- 复杂任务：维护 `task_plan.md`、`findings.md`、`progress.md`。
- 发布或高风险任务：按 `progress.md` 记录 `Changed Files Manifest`、`Verification Waivers` 和必要 UI/浏览器证据。
- 长期知识：稳定结论提炼到 `.agents/references/`，不要只留在三文件或任务归档里。

## Long-lived Knowledge
| file | purpose |
|---|---|
| `.agents/references/project-conventions.md` | 项目约定、验证命令、交付规则 |
| `.agents/references/architecture-notes.md` | 架构边界、模块职责、关键模式 |
| `.agents/references/common-pitfalls.md` | 高频坑点、正确检查方式 |
| `.agents/references/requirements-index.md` | 需求入口和优先级 |
| `.agents/references/feature-index.md` | 功能清单、状态和 QA 入口 |
| `.agents/references/tooling-map.md` | 外部工具登记和阻断策略 |

## Collaboration Rules
- 开始复杂任务前，先确认真实 Git 边界、当前分支、已有脏文件和任务拥有文件。
- 不修改无关脏文件，不顺手重排无关代码，不把生成物混入业务提交。
- 如果项目存在多个子仓库或非标准 Git 边界，在 `progress.md` 的 `Changed Files Manifest` 记录 `repo / branch / base` 和 `collaboration notes`。
- 需要架构、接口、数据流或领域语义变化时，在 `task_plan.md` 的 `Architecture Impact` 记录影响，并按需更新 `architecture-notes.md`。

## Browser / Deploy Notes
- 浏览器回归入口：待填写 / not-needed
- 部署入口：待填写 / not-needed
- 回滚方式：待填写 / not-needed

## Handoff
- 当前任务状态以根目录三文件为准。
- 已完成任务归档到 `.agents/tasks/YYYYMMDD-short-slug/`。
- 新会话接手时，优先读取 `progress.md` 的 `Handoff`，再按任务需要读取最小相关 references。
