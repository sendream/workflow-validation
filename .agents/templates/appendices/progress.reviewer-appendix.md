# Progress Appendix: Role Reviewer

> Snippet only. Copy relevant sections into root `progress.md` when Role Reviewer assessment is triggered. This file is not task state.

## Isolated Reviewer
> Legacy-compatible heading for validator support; semantically this is the Role Reviewer assessment. New prose should use `Role Reviewer`.

| item | value |
|---|---|
| Required assessment | yes / no |
| Trigger decision | not-needed / assessment-only / preferred |
| Reason | risk / external-system / auth / DB / deploy / rollback / waivers / dirty-worktree / long-session / not-triggered |
| Authorization scope | none / policy-auto / task / session / external-standing-opt-in / revoked |
| Authorization source | AGENTS.md Policy-Auto Reviewer / user message / task instruction / external standing opt-in / not-needed |
| Start required | yes / no / not-needed |
| Runtime policy status | not-checked / allowed / runtime-policy-blocked / explicit-delegation-required / explicit-denied / revoked / not-needed |
| Start result | not-needed / policy-auto-started / task-authorized-started / session-authorized-started / external-opt-in-started / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / budget-exceeded / explicit-denied |
| Reviewer tool | Codex subagent / Gemini / Claude / other / unavailable / runtime-policy-blocked / not-needed |
| Model policy | inherit-main-model / external-reviewer / not-needed |
| Reasoning effort | xhigh / inherited / not-needed |
| Timeout policy | review-incomplete / reviewer-timeout / not-needed |
| Runtime-enforced budget | hard-timeout / hard-turn-limit / hard-file-limit / prompt-soft-limit / manual-fallback / not-needed |
| Input package | `.agent-state/runs/<run_id>/role-review/<role>/` / legacy `.agent-state/runs/<run_id>/isolated-review/` / not-created / not-needed |
| Packet validator status | pass / fail / not-run / not-needed |
| Packet validator command | `.agents/scripts/validate-role-review-packet.py --root . --packet ... --risk-tier high --format json` / not-needed |
| Packet validator exit code | 0 / nonzero / not-needed |
| Packet validator artifact | `.agent-state/runs/<run_id>/role-review/<role>/packet-validator.json` / not-needed |
| Packet retention | retained-during-active-task / not-retained-after-submission / not-needed |
| Durable review summary | `docs/evidence/<review-summary>.md` / `.agents/tasks/<task-id>/summary.md` / not-needed |
| Review focus | quality / security / test-coverage / release-risk / mixed / not-needed |
| Secret handling | redacted / metadata-only / not-needed |
| Verdict | pass / needs-more-evidence / blocking / review-incomplete / review-unverified / not-needed |
| Disposition | accepted / rejected / needs-more-evidence / deferred / not-needed |
| Fallback | local S0/S1 red-team / runtime-policy-blocked / explicit-delegation-required / tool-unavailable / packet-invalid / brief-invalid / validator-failed / review-incomplete / reviewer-timeout / explicit-denied / not-needed |

## Reviewer Start Authority
> `policy-auto` 是 G16 已路由后内部只读 reviewer 的项目级 start authority；当前仅对 high / release / external-system 任务开放。档位本身不触发 assessment、不优先 reviewer、不构成启动理由。它不能覆盖系统 / 开发者 / 工具调用政策。外部模型 reviewer、写入型 worker、deploy / DB write / push / external-write、secrets 访问、超过 reviewer 数量上限，仍必须用户明确授权。授权只对当前 active task / run_id / repo path 有效，任务切换、目标路径变化、权限扩大、跨会话恢复或进入 external-write 时自动失效。`Scope=implementation-worker` 不是 Role Reviewer 的一种；默认不存在，只有用户另行授权且写入范围隔离时另案启用。`Authorized roles` 指本次授权覆盖的挑战焦点，不是编制；新 Brief 推荐 `requirements` / `security` / `release`，其余 token 仅兼容。

| item | value |
|---|---|
| Authority mode | policy-auto / task-authorized / session-authorized / external-standing-opt-in / not-needed |
| Authority source | AGENTS.md Policy-Auto Reviewer / user message / task instruction / external standing opt-in / not-needed |
| Scope | read-only reviewer / implementation-worker / external-write / not-needed |
| Active task id | `<task_id>` / not-needed |
| Run ID | `<run_id>` / not-needed |
| Repo path | 待填写 / not-needed |
| Authorized roles | requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed / not-needed |
| Max reviewers | 0 / 1 / 2 / explicit-budget / not-needed |
| External model allowed | no / yes-with-standing-opt-in / not-needed |
| Expires | active task completion / target path change / permission expansion / cross-session recovery / external-write / not-needed |
| Runtime policy status | not-checked / allowed / runtime-policy-blocked / explicit-delegation-required / explicit-denied / revoked / not-needed |
| Runtime-enforced budget | hard-timeout / hard-turn-limit / hard-file-limit / prompt-soft-limit / manual-fallback / not-needed |

## Role Review Summary
> `role` / `Authorized roles` 指本次授权覆盖的挑战焦点，不是编制。新 Brief 推荐 `requirements` / `security` / `release`；其余 token 仅兼容。

| role | trigger | packet | focus | verdict | disposition | unresolved risk |
|---|---|---|---|---|---|---|
| not-needed / requirements / plan-consistency / architecture / qa / security / release / knowledge / docs-api / mixed | 待填写 | `.agent-state/runs/<run_id>/role-review/<role>/` / legacy `.agent-state/runs/<run_id>/isolated-review/` / not-needed | quality / security / test-coverage / release-risk / knowledge-promotion / mixed | pass / needs-more-evidence / blocking / incomplete / not-needed | accepted / rejected / needs-more-evidence / deferred / not-needed | none / 待填写 |
