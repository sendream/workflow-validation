# Gate Cards

Owner: project `AGENTS.md` routes; this file owns triggered-gate detail.
Boundary: reference-only; not a runner, task state source, delivery approval, or authorization substitute.

Read exactly the card selected by the project route. Do not load this file wholesale for a fast task. Where a card links to a workflow reference or validator, that linked asset owns its detailed schema and implementation.

## Rule ownership inventory

| rule family | single authoritative owner | callers may do | callers must not do |
|---|---|---|---|
| active task identity, lifecycle and migration | G06_ACTIVE_MIGRATION | link the card and shared snapshot | parse root state independently or create state files |
| review/audit write authorization | G00_REVIEW_AUTH | route to the card | treat a finding as write authorization |
| code-review tier and findings | G19_CODE_REVIEW | select the review tier | start a role reviewer or authorize changes |
| test evidence and verification waiver | G10_TEST_EVIDENCE | request evidence or a typed waiver | convert an unverified claim into PASS |
| task closeout | G21_TASK_CLOSEOUT | require the named closeout validator when triggered | become a general runner, second ledger, or Workflow Trace owner |
| workflow trace applicability | `progress.core.md#Appendix Triggers` | copy the matching appendix when that row fires | treat high/release, G21, or the validator as the applicability owner |
| workflow trace schema | `progress.workflow-trace-appendix.md` | fill the copied section; run `validate-workflow-trace-consistency.py` only as enforcement | treat the validator as the rule owner or make Trace a second state source |
| external skill/tool intake | G22_EXTERNAL_SKILL | classify a candidate and require explicit approval | install, enable, globalize, or grant permissions |

Precedence is fixed: user authorization → nearest project `AGENTS.md` route → this card → linked workflow detail → deterministic validator. Global `AGENTS.md` supplies only cross-project safety rules and never project facts.

## G00_REVIEW_AUTH

| field | value |
|---|---|
| trigger | review, audit, assessment, retrospective, or a finding may turn into implementation |
| independent_failure_mode | a read-only finding silently becomes a write or delivery authorization |
| required_inputs | user intent, target path, allowed write scope, prohibited actions |
| evidence | `progress.md#Review / Audit Boundary`; `validate-review-authorization.py` when strict |
| failure_route | stop at report-only output and ask for scoped authorization |
| cost_class | low; read only when review/audit context exists |
| owner | G00_REVIEW_AUTH |
| retire_or_downgrade_when | never; it is an authorization boundary |

Detail: `reviewer-governance.md` for reviewer mechanics and `code_review.md` for quality review.

## G03_CLARIFICATION

| field | value |
|---|---|
| trigger | goal, output, non-goal, acceptance, data/permission, validation, or scope changes the implementation choice |
| independent_failure_mode | an irreversible implementation proceeds on an unrecorded assumption |
| required_inputs | blocking ambiguity that source lookup cannot settle, and 2-4 mutually exclusive options when practical |
| evidence | answer landing in Requirement Contract, assumptions, scope, negative constraints, scenarios, matrix, or not-needed |
| failure_route | ask only the current decision frontier, record a conservative non-blocking assumption, or stop for a bounded probe |
| cost_class | low; only for decision-changing ambiguity |
| owner | G03_CLARIFICATION |
| retire_or_downgrade_when | current decision-changing ambiguity is resolved, evidence-owned, or blocked; dependent future branches do not keep G03 active |

Detail: `routing-planning.md`.

## G04_SCOPE_BRAKE

| field | value |
|---|---|
| trigger | scope exceeds the minimal file set, about 10 source files, 3+ modules, or a local fix repeatedly broadens |
| independent_failure_mode | unbounded refactor hides acceptance and verification risk |
| required_inputs | original goal, proposed extra files, reason, verification and rollback impact |
| evidence | Scope Control / plan update or explicit user-approved wider scope |
| failure_route | split, defer, or ask before expanding |
| cost_class | low; only after measurable expansion |
| owner | G04_SCOPE_BRAKE |
| retire_or_downgrade_when | scope returns to a bounded accepted slice |

Detail: `routing-planning.md`.

## G06_ACTIVE_MIGRATION

| field | value |
|---|---|
| trigger | workflow assets change while an active complex, high, or release task continues |
| independent_failure_mode | stale or conflicting root task state is silently reused |
| required_inputs | root three files and bounded shared snapshot |
| evidence | `validate-active-task-migration.py`; snapshot source status and digests |
| failure_route | reconcile task id, phase, route, and evidence before continuing |
| cost_class | medium; active complex task only |
| owner | G06_ACTIVE_MIGRATION |
| retire_or_downgrade_when | task is archived or no active complex task remains |

Detail: `routing-planning.md`; parser implementation: `current_task_snapshot.py`.

## G09_BEHAVIOR_CONTRACT

| field | value |
|---|---|
| trigger | an observable behavior change, and either high/release or a field/API/permission/compatibility/cross-layer/negative-boundary contract |
| independent_failure_mode | happy-path implementation misses observable behavior or risk case |
| required_inputs | Requirement Contract, observable outcomes, major negative or boundary case |
| evidence | Behavior Scenarios / Example Table linked to Verification Matrix; explicit not-needed is allowed |
| failure_route | add the smallest behavior contract or record why it is not needed |
| cost_class | medium; not a default ordinary bugfix tax |
| owner | G09_BEHAVIOR_CONTRACT |
| retire_or_downgrade_when | no behavioral contract trigger exists |

Detail: `routing-planning.md` and `verification-evidence.md`.

## G10_TEST_EVIDENCE

| field | value |
|---|---|
| trigger | behavior change, defect repair, required verification, waiver, high/release, or terminal PASS claim |
| independent_failure_mode | a claim of PASS lacks replayable evidence or a waiver lacks scope and substitute evidence |
| required_inputs | acceptance/risk, command or artifact, result, applicable waiver and owner |
| evidence | Verification Matrix, Final Evidence Ledger, `.agent-state/runs/<run_id>/manifest.json` when command evidence is required |
| failure_route | run focused verification, mark unverified, or write a complete typed waiver |
| cost_class | proportional to risk; never require all tools by default |
| owner | G10_TEST_EVIDENCE |
| retire_or_downgrade_when | evidence is complete or the task route does not require it |

Detail: `verification-evidence.md`. Mechanical PASS bind: `validate-claim-evidence.py`. Also traceability and evidence-waivers.

## G14_STRUCTURAL_INDEX

| field | value |
|---|---|
| trigger | cross-module structure analysis, explicit Graphify/CodeGraph request, or project-level trial |
| independent_failure_mode | stale/generated index output is treated as source fact or hooks generate an index |
| required_inputs | project provider/status, source-root freshness, explicit query/refresh authorization |
| evidence | source-confirmed query evidence or explicit trial record |
| failure_route | use targeted source search; expose stale/missing state rather than claiming freshness |
| cost_class | optional and explicit |
| owner | G14_STRUCTURAL_INDEX |
| retire_or_downgrade_when | source search answers the question or trial shows no value |

Detail: `tooling-safety.md` and `project-conventions.md`.

## G16_ROLE_REVIEWER

| field | value |
|---|---|
| trigger | explicitly requested read-only challenge, or residual semantic risk recorded after deterministic checks; high/release alone does not select this card |
| independent_failure_mode | reviewer is started without authority/budget or skipped without a typed assessment |
| required_inputs | risk route, assessment, start authority, Agent Brief, policy, budget and fallback |
| evidence | reviewer assessment and packet/result validator where started |
| failure_route | retain deterministic checks; record non-start or incomplete typed result |
| cost_class | high; default start count is 0 |
| owner | G16_ROLE_REVIEWER |
| retire_or_downgrade_when | measured calibration shows a narrower route is equivalent |

Detail: `reviewer-governance.md`.

## G17_SHIP_CHECK

| field | value |
|---|---|
| trigger | explicit ship-check, delivery decision, or release handoff |
| independent_failure_mode | delivery recommendation ignores acceptance, evidence, scope, or remaining risk |
| required_inputs | changed scope, focused evidence, unresolved risks and relevant gate results |
| evidence | concise delivery recommendation with conditions and handoff |
| failure_route | return no or conditional delivery recommendation |
| cost_class | focused for standard; high-risk addendum only when routed |
| owner | G17_SHIP_CHECK |
| retire_or_downgrade_when | no delivery decision is requested |

Detail: delivery recommendation is owned here; do not load a wrapper Skill.

## G18_RELEASE_SOURCE

| field | value |
|---|---|
| trigger | release/external-system creates a deployable jar, dist, container, or package |
| independent_failure_mode | a release artifact has unknown or dirty source provenance |
| required_inputs | source mode, intended files, artifact identity, dirty disposition and rollback point |
| evidence | release-source packet and validator result |
| failure_route | block, or require explicit user risk acceptance plus complete waiver |
| cost_class | release-only |
| owner | G18_RELEASE_SOURCE |
| retire_or_downgrade_when | no deployable artifact is produced |

Detail: `verification-evidence.md`.

## G19_CODE_REVIEW

| field | value |
|---|---|
| trigger | standard-or-higher behavior change, requested review, commit/push, or residual quality risk |
| independent_failure_mode | a defect or scope drift reaches handoff without a proportionate quality check |
| required_inputs | diff, acceptance, risk tier, focused test evidence and known constraints |
| evidence | micro/local/enhanced review result with blocking and non-blocking findings separated |
| failure_route | fix, record condition, or return review-only findings without implementation authorization |
| cost_class | micro for low; local for standard; enhanced only when routed |
| owner | G19_CODE_REVIEW |
| retire_or_downgrade_when | no code behavior changed and no review is requested |

Detail: `code_review.md`.

## G20_PUSH_OVERLAY

| field | value |
|---|---|
| trigger | commit, push, delivery package cleanup, or staged workflow files |
| independent_failure_mode | local workflow overlay, secret, runtime data, or generated noise leaks into delivery |
| required_inputs | staged diff, dirty classification, local excludes and delivery scope |
| evidence | overlay-boundary validator and appropriate review/waiver result |
| failure_route | unstage/exclude safely; never delete local workflow assets as cleanup |
| cost_class | delivery-only |
| owner | G20_PUSH_OVERLAY |
| retire_or_downgrade_when | no delivery action is requested |

Detail: `lifecycle-recovery.md` and overlay-boundary validator.

## G21_TASK_CLOSEOUT

| field | value |
|---|---|
| trigger | high/release/external closeout, submitted state, archive, or explicit closeout request |
| independent_failure_mode | final handoff has stale lifecycle, duplicate fact checks, or missing evidence trace |
| required_inputs | shared snapshot, final ledger, triggered fact-domain evidence, concrete next action or stop condition |
| evidence | `validate-task-closeout.py` when strict closeout is applicable; Git/delivery facts are checked at their owning boundary |
| failure_route | expose the named fact-domain error; do not create a second ledger or runner |
| cost_class | high only on routed closeout |
| owner | G21_TASK_CLOSEOUT |
| retire_or_downgrade_when | low/standard task has no strict closeout trigger |

Detail: `lifecycle-recovery.md` and validator map.

## G22_EXTERNAL_SKILL

| field | value |
|---|---|
| trigger | external skill, plugin, connector, or MCP capability is proposed; not an internal hook, validator, or command edit |
| independent_failure_mode | catalog text silently enables permissions, network, writes, or a second workflow |
| required_inputs | capability card, trust/provenance, scope, limits, approval, isolation and rollback |
| evidence | validated capability card and explicit task-level authorization |
| failure_route | keep it report-only or reject; do not install/connect automatically |
| cost_class | explicit-only |
| owner | G22_EXTERNAL_SKILL |
| retire_or_downgrade_when | candidate is rejected or its card expires |

Detail: `tooling-safety.md` and capability-card contract.
