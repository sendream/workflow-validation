# Harness Components

Status: reference-only component registry / Control Ledger
Runtime authority: none
Default loading: no

This file is not a gate, not a runner, not a state source, not a validator, and not delivery approval. It gives stable names to workflow harness mechanisms so validators, evals, reports, stale assumptions, and future cleanup work can point at the same component without copying the component rules.

It is also the reference-only Control Ledger: it records why a stable mechanism exists, which independent failure it covers, its trigger/cost/evidence, and when it must be re-evaluated. A row never grants permission to start a reviewer, deploy, push, enable a plugin/MCP, install a skill, access secrets, write externally, or alter task state.

Do not use this file to authorize reviewer startup, deploy, push, plugin or MCP enablement, global skill install, external writes, DB writes, secret access, hook changes, or workflow state changes. Fast path and ordinary standard tasks do not need to read this registry.

## Architecture Modules

Architecture module IDs describe stable harness responsibilities. They are not report recommendations and cannot be adopted, retired, or scored as mechanisms.

| architecture_id | responsibility | owner_contracts | default_loading |
|---|---|---|---|
| task-spec-routing | classify work and bind requirements to an execution path | `AGENTS.md`; `workflow/routing-planning.md` | routed only |
| context-knowledge | select bounded context and preserve project knowledge boundaries | `workflow/context-memory.md`; `context-select.py` | routed only |
| capability-execution | expose safe tools, skills, hooks, and structural queries | `workflow/tooling-safety.md`; `tooling-map.md` | explicit or routed |
| lifecycle-recovery | maintain active-task continuity, failure recovery, archive, and closeout | `workflow/lifecycle-recovery.md` | phase-routed |
| observation-evidence | capture run observations and replayable evidence without becoming task state | `workflow/verification-evidence.md`; `validate-run-manifest.py` | evidence-producing tasks |
| verification-eval | check behavior, contracts, regressions, and evidence claims | `validator-map.md`; workflow eval scripts | routed validation |
| governance-human | enforce authorization boundaries and surface bounded human decisions | `workflow/reviewer-governance.md`; human-decision appendix | risk-routed |
| evolution-experiment | evaluate, pilot, adopt, narrow, roll back, or reject harness changes | `workflow/evolution-experiments.md`; `workflow-value-report.py` | explicit experiment only |

## Mechanism Registry

| component_id | status | owner_files | gate_or_alias | validators_or_reports | eval_cases | boundary | value_signal | retirement_signal | control_type | enforcement | trigger | independent_failure_mode | evidence | cost_class | conflicts_or_dependencies | ablation_or_expiry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| evidence-governance | active | `AGENTS.md`; `workflow/verification-evidence.md`; `progress.md`; `validate-evidence-waivers.py` | Final Evidence Ledger / Verification Waivers | `validate-evidence-waivers.py`; `workflow-value-report.py` | case-24; case-48; behavior evidence fixtures | evidence artifact only; not task state | PASS/WAIVED claims bind to replayable evidence or explicit waiver | repeated low-risk tasks show ledger cost with no missed evidence reduction | sensor | hard for claimed PASS/WAIVED evidence; otherwise report-only | evidence-producing focused/assured task or explicit waiver | completion claim cannot be replayed or its limitation is hidden | command result, artifact reference, explicit waiver | medium; should not run for fast tasks without evidence claims | depends on active-state/evidence schema; must not duplicate task-closeout parsing | re-evaluate when schema, model/tool telemetry, or evidence reuse rules change |
| release-provenance | active | `AGENTS.md`; `workflow/verification-evidence.md`; `validate-release-artifact-source.py`; release appendices | G18_RELEASE_SOURCE | `validate-release-artifact-source.py`; `workflow-value-report.py` | case-37; release-source behavior fixtures | provenance artifact only; not delivery approval | release artifacts bind to intended source files, source manifest, and artifact hash | clean-source/current-cohort evidence proves simpler path has no provenance loss | sensor | hard on release-source claims | release/external delivery artifact with source assertion | formally valid artifact manifest does not match actual source/artifact | source manifest, hash, validator result | high; release-only | depends on release route and evidence-governance; cannot be replaced by generic closeout | re-evaluate only with a replacement provenance control and adversarial fixture parity |
| task-closeout | active | `AGENTS.md`; `workflow/lifecycle-recovery.md`; `validate-task-closeout.py` | G21_TASK_CLOSEOUT | `validate-task-closeout.py`; `workflow-value-report.py` | case-52; closeout behavior fixtures | closeout check only; not new work authorization | terminal task has a concrete next action or stop condition and no unresolved material evidence blocker | closeout repeatedly adds no quality signal for a task class | sensor | hard only on routes whose closeout contract requires it | explicit closeout or assured lifecycle transition | task is marked complete with missing evidence, a vague next action, or inconsistent active state | shared current-task snapshot plus closeout validator result | medium/high by route | depends on evidence-governance and release-provenance; should share parsing, not duplicate facts | re-evaluate per route after coverage map shows a lower-cost equivalent |
| role-reviewer | active | `AGENTS.md`; `workflow/reviewer-governance.md`; `code_review.md`; `role-review-packet.md` | G16_ROLE_REVIEWER / Policy-Auto | `validate-reviewer-assessment.py`; `validate-role-review-packet.py`; `validate-task-closeout.py`; `workflow-value-report.py` | case-35; case-39; case-47 | read-only challenge; not implementation authorization | accepted findings or risk reductions exceed reviewer flow tax | high/release cohort shows low accepted finding rate and high incompletion | adapter | risk-routed hard requirement only where project policy says so | high/release or residual semantic risk after deterministic checks | permission, concurrency, data, design, or rollback defect escapes deterministic checks | finding-evidence-risk-recommendation packet and calibration metrics | high; model/reviewer wall time | must not start after a deterministic red failure; conflicts with duplicate review checklists | re-evaluate on model/reviewer/profile change and accepted-finding/false-positive drift |
| dynamic-agent-campaign | optional | `workflow/reviewer-governance.md`; `validate-dynamic-agent-campaign.py`; campaign templates | dynamic multi-reviewer campaign | `validate-dynamic-agent-campaign.py`; `workflow-value-report.py` | case-49; campaign behavior fixtures | derived campaign artifact only; not runner/state source | multi-reviewer campaign changes main plan or catches severe issue | campaign metrics show repeated low value or excessive cost | adapter | explicit trial only | independently reviewable packets with user-approved campaign | breadth of independent review misses a severe issue | task split, packet schema, all-agent telemetry, deterministic integrator result | very high | depends on isolated worksets and role-reviewer; never a default fallback | expire after a failed or incomplete telemetry trial; re-admit only with new evidence |
| structural-index | explicit-trial | `AGENTS.md`; `workflow/tooling-safety.md`; `project-conventions.md`; `tooling-map.md` | G14_STRUCTURAL_INDEX / CodeGraph / Graphify | `validate-workflow-trace-consistency.py`; `workflow-value-report.py` | case-31; case-57 | read-only query or explicit trial; not automatic index/watch | query changes decision, finds tests/files, or prevents wrong edit | repeated empty/false-negative outputs or costly refresh without decision change | adapter | explicit read-only trial | cross-module navigation remains unresolved after bounded search | map hides relevant local code or stale graph is trusted as fact | source digest/stale marker, query result, source confirmation | medium/high refresh cost | conflicts with automatic watch/rebuild; source search is the fallback | re-evaluate after generator/source-root changes or no decision-changing queries |
| skill-governance | active | `validate-local-skills.py`; `skill-curator-report.py`; `validate-skill-curator-report.py`; skill references | skill evolution / curator | `validate-local-skills.py`; `skill-curator-report.py`; `validate-skill-curator-report.py`; `workflow-value-report.py` | case-21; case-36; case-58 | report-only unless explicit user approval; no auto install/update/globalize | observed skill utility, reduced misses, low negative transfer | stale/false-trigger/maintenance signals outweigh observed use | guide | report-only for curation; task trigger is routed | skill has a unique, evidenced capability and no conflicting simultaneous load | rules are duplicated, stale, or conflict when multiple skills match | skill metadata, route tests, source digest, usage/ablation result | low at runtime if metadata is thin; high if long skills co-load | depends on thin AGENTS and Gate Cards; conflicts must be declared | re-evaluate whenever skill, trigger, model, or source digest changes |
| archive-memory | active | `.agents/tasks/README.md`; `create-task-archive.py`; `validate-task-archive-hygiene.py`; `search-workflow-history.py` | summary-first archive / manifest-first history | `validate-task-archive-hygiene.py`; `validate-run-manifest.py`; `search-workflow-history.py`; `workflow-value-report.py` | case-50; archive behavior fixtures | completed-task archive and derived search only; not active task state | history can be recovered through summary/manifests without raw-log reads | archives repeatedly add noise without retrieval or recovery value | guide | report-only for retrieval choice | rollover, recovery, or explicit history query | active task loses a verified decision or re-reads raw logs unnecessarily | archive summary, manifest reference, retrieval outcome | low when queried; high if injected by default | depends on current-task snapshot; must not become a fourth active-state source | re-evaluate on retrieval miss/noise rate or archive schema change |

## Signal Classes

Signal classes calibrate mechanisms; they are not adoptable components and cannot be used as workflow attribution targets.

| signal_id | signal_class | owner_files | boundary |
|---|---|---|---|
| flow-tax | cost | `workflow-value-report.py`; `workflow/evolution-experiments.md`; `validator-map.md` | report-only calibration signal; not a gate, task state, or delivery approval |

## Control Family Coverage

This table has no runtime component IDs and must not be used for run-manifest attribution. It exists to prevent major default-cost controls from being omitted merely because their stable component IDs have not yet been introduced through a separately tested migration.

| control_family | current_owner | target_decision | required future contract |
|---|---|---|---|
| instruction-kernel | global/project `AGENTS.md` | retain, thin, and assign one owner per rule | precedence, route, independent failure mode, default token budget, conflict check |
| current-task-state | root three files and their consumers | retain source of truth; shared bounded snapshot is implemented; keep cost claim in explicit trial | snapshot schema, bounded reads, partial-state behavior, no fourth persistent state |
| context-selector | `context-select.py` | workflow-reference selector and thin skill/Gate Card entry are implemented; keep cost claim in explicit trial | routing evidence, negation handling, initial/current/forecast budget, measured/inferred status |
| hook-profile | full profile `planning-hook.py` and `hook-dispatch.sh` | retain narrow guard; assist lifecycle events are narrowed and full remains explicit opt-in | event/payload/TTY/timeout/output/block semantics, lock observability, cost ceiling |
| deterministic-validation | smoke/eval/validator scripts | merge ownership, retain independent safety checks | coverage map, primary owner, positive/negative fixture, runtime duration budget |
| external-capability | `workflow/tooling-safety.md`; `capability-card.md`; `validate-capability-card.py` | static admission only; no enablement | trust, scope, task-level approval, isolation, data flow, rollback, idempotency, expiry, no-permission-change result |
| compatibility-adapter | `state_compat.py`; `state-compat.py`; `.agent-state/README.md` | current-first read-only lookup; retain legacy only through the stated window | selected path, origin, deprecated flag, reason, deprecated_since, remove_after, conflict fixture |

## Rules

- Add a new component only when at least two workflow surfaces need a shared ID.
- Keep detailed rules in owner files; this registry only links to them.
- A Control Ledger row must identify an independent failure mode, trigger, evidence, cost class, dependency/conflict and ablation/expiry. Missing fields make the control a candidate for report-only status, merge, downgrade or retirement; they do not authorize a new gate.
- Control-family coverage is a planning aid, not an attribution API. Add a new `component_id` only together with the code, parity, smoke and behavior-eval changes that recognize it.
- Public benchmarks, advisory catalogs, visible behavior fixtures, and smoke checks are not held-out evidence.
- Unknown `component_id` values in workflow-source attribution are handled by explicit workflow-source validators or evals; this registry only lists stable component IDs.
