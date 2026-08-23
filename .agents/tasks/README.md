# Task Archives

## Purpose
归档已完成复杂任务的三文件，避免长期项目里 `task_plan.md`、`findings.md`、`progress.md` 无限膨胀。

`.agents/tasks/` 是归档 / handoff 资产，不是运行中的 active task 状态目录。
运行中的临时状态、日志、锁、flag 和 run evidence 一律写入 `.agent-state/`。

## Archive rule
复杂任务完成、验收通过并完成必要 commit / push 检查后，最后把项目根三文件复制到：

```text
.agents/tasks/YYYYMMDD-short-slug/
├─ summary.md
├─ task_plan.md
├─ findings.md
└─ progress.md
```

如果当前 Codex sandbox 或文件权限导致 `.agents/tasks/` 不可写，不要阻断交付。
改为输出归档建议，或把待归档文件复制到：

```text
.agent-state/tasks/archive-ready/YYYYMMDD-short-slug/
```

## Keep current root clean
- 项目根三文件只表示当前任务或当前阶段。
- 已完成任务进入 `.agents/tasks/`。
- 规划、执行和验证阶段不得依赖写入 `.agents/tasks/`。
- 新会话、review 或恢复历史时先读归档目录的 `summary.md`；只有需要审计具体证据或恢复旧任务细节时，才读取完整 `task_plan.md`、`findings.md`、`progress.md`。
- 旧归档如果没有 `summary.md`，先补一个短摘要；不要默认读取 `progress.before*`、`findings.full*`、长日志或完整历史流水。
- 不把运行日志、大文件、构建产物、截图和临时调试文件放进 `.agents/tasks/`。
- 如果任务需要长期沉淀，把稳定结论提炼到 `.agents/references/`，不要只留在归档里。

## Summary schema
- 新归档的 `summary.md` 使用 `.agents/templates/task_archive.md`。
- `task_path` 和 `risk_tier` 分开记录：`fast path` 不是 Risk Tier。
- `summary.md` 必须标注 `reference-only`。
- `next_task_or_follow_up` 只作为历史提示，不是 backlog、issue tracker 或当前任务指令。
- `Recall Metadata (Optional)` 可记录短 `event`、`entities`、`source_refs`，只用于提高历史检索命中率和可解释性。
- `event / entities / source_refs` 不是知识图谱、不是任务状态、不是自动注入上下文；不要填 raw logs、HAR、截图、DB dump 或长输出。
- 新归档可用 `.agents/scripts/validate-task-archive-hygiene.py --archive .agents/tasks/<task-id> --strict-new` 检查。

## Helper

可显式使用归档 helper 生成 summary-first archive：

```bash
.agents/scripts/create-task-archive.py --root . --task-id YYYYMMDD-short-slug --status completed --dry-run
.agents/scripts/create-task-archive.py --root . --task-id YYYYMMDD-short-slug --status completed --apply
.agents/scripts/validate-task-archive-hygiene.py --root . --archive .agents/tasks/YYYYMMDD-short-slug --strict-new
```

该 helper 只读取根 `task_plan.md`、`findings.md`、`progress.md`，生成 `summary.md` 并复制三文件；它不读取 raw logs，不清空根三文件，不执行 closeout，不替代人工裁决或验证证据。

## Naming
- 日期使用本地日期：`YYYYMMDD`
- `short-slug` 用 2 到 5 个英文单词或拼音短词
- 示例：`20260422-login-copy-cleanup`
