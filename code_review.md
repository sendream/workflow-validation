# Code Review

Owner: G19_CODE_REVIEW in `.agents/references/workflow/gate-cards.md`. This file selects a proportionate quality check; it is not implementation authorization, a task-state source, or a replacement for deterministic validation.

## Select the smallest review tier

| tier | use when | minimum output |
|---|---|---|
| `not-needed` | no behavior change and no review request | reason recorded |
| `micro-local-check` | fast path / `low` small behavior change | scope, focused verification, obvious risk scan |
| `local-checklist` | `standard` behavior change or requested local review | machine-first evidence plus short semantic review |
| `enhanced-review` | `high` / `release` / `external-system` residual risk | local checklist plus G16 assessment and typed fallback/result |

Review finding is not implementation authorization. In review-only work, report findings and ask for scoped write authorization before fixing. Findings are labeled `direct / indirect / unverified`; only direct evidence can support a blocking conclusion. Record accepted findings and repair evidence in the Review Finding Closure Map when that map is required by the routed task.

## Local checklist

1. Start with machine verification matching the changed behavior: focused test, lint, typecheck, build, API smoke, browser check, or `.agents/scripts/tooling-router.py --mode plan/run` when routed. Do not substitute a passing build for behavior evidence.
2. Check requirement alignment, Scope / Negative Constraints, Architecture Impact, failure and permission paths, and avoid unneeded abstractions or compatibility logic.
3. Check the evidence is replayable: command/result, `scenario_id` where applicable, artifact or QA note, and a complete waiver when a required check did not run. `Test Evidence Gate`, `Test Strategy Ladder`, Grill Check and defect closure details live in G10's linked reference.
4. Check Diff-to-plan and handoff: planned versus changed files, known risk, Knowledge Promotion / Known-Bad Path Promotion only if triggered, and no untracked runtime artifacts, secrets or generated noise.

## Documentation review

- Keep each standing rule in one authoritative home; link from other locations instead of restating it.
- Standing docs describe the current contract. Put change history, execution status and reasoning traces in task artifacts, archives, evidence or an existing project decision record.
- Remove derivation transcripts, split wall-of-text paragraphs and avoid undifferentiated bold / CAPS emphasis.

## Role Reviewer consumption

G16 owns reviewer startup and authority in `.agents/references/workflow/reviewer-governance.md`; this guide only consumes its result. high/release 单独不要求 assessment；评估不等于启动. `enhanced-review` does not authorize writes, deployment, external calls, secrets access, or a second workflow. If the reviewer is unavailable or `runtime-policy-blocked`, retain the deterministic checks and record the typed non-start/fallback rather than inventing a PASS.

## Delivery-focused checks

For commit, push, release or external-system work, also route to G20/G18/G21. Confirm staged diff scope, overlay boundary, dirty-worktree classification, Release Artifact Source Gate where an artifact exists, final evidence/waiver status, rollback point and unresolved blockers. `tooling-map.md` and `tooling-router.py` are the only tool-routing sources; an `approval-required` result is not permission to continue.

## Output

List blocking findings before non-blocking items, with location, evidence and required next action. If no clear finding exists, say so and state the remaining verification gap or risk.
