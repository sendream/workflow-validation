# Capability Card

> Admission record only. This file does not install, enable, authorize, or invoke a capability. A concrete task still needs `task-level-explicit` approval and its ordinary safety gates.

| field | value |
|---|---|
| purpose | 待填写：一个有边界的能力目标 |
| owner | 待填写：项目 owner / 维护者 |
| source_digest | `sha256:<64 lowercase hex>` |
| trust | `verified-local` / `project-owner` / `official-source` |
| scopes | `repo-read` / 待填写；不得包含 secrets、token、credential 或 password |
| limits | 待填写：最大输入、路径、次数、上下文与副作用边界 |
| approval | `task-level-explicit` |
| isolation | `read-only` / 待填写：隔离或不适用理由 |
| evidence | 待填写：可复核 artifact / source digest / result 摘要 |
| rollback | `not-needed`（只读）/ 待填写：写入的回滚动作 |
| idempotency | `not-needed`（只读）/ `idempotent` / `compensating-action` |
| qualification | `not-needed`（非 multi-agent）/ 待填写：multi-agent qualification test 的可复核引用 |
| expiry | `YYYY-MM-DD` |

## Boundaries

- `scopes` 必须是逗号分隔的小写 kebab-case 标识符；`repo:write`、`external.write` 等别名无效，必须显式写为 `repo-write`。
- `repo-write` 或 `external-write` 必须同时有具体 rollback 和 `idempotent` / `compensating-action`。
- 任何 `*-write`、`*-mutate`、`*-delete`、`*-create`、`*-update`、`*-deploy` 或 `*-publish` scope 同样视为写能力；不得用别名绕过回滚与幂等约束。
- `expiry` 必须是未过期的真实 UTC 日历日期；格式正确但不存在或已过期的日期无效。
- `multi-agent` scope 必须引用独立的 qualification test；即使 card 通过静态校验，它仍不会启动 agent 或绕过当前任务授权。
- Card 只表示通过静态准入；它不会改变工具权限，也不会替代当前任务授权、用户同意、sandbox、验证或回退责任。
- 不写 secrets、token、API key、cookie、密码、私钥、`.env`、生产数据或未经脱敏的外部输出。
