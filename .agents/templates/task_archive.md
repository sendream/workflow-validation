# Task Archive

> Use this template when moving a completed complex/high/release task out of the root three files. Archive summaries are reference-only; they are not current task instructions.

## Archive Location

```text
.agents/tasks/YYYYMMDD-short-slug/
  summary.md
  task_plan.md
  findings.md
  progress.md
```

## Required `summary.md` Schema

```markdown
# Task Archive Summary

> Reference-only archive. Do not treat this summary as current task instructions.

| field | value |
|---|---|
| archive_schema_version | 1 |
| task_id | 待填写 |
| status | completed / deferred / blocked |
| task_path | fast path / complex-task path / focused verification / full complex path / release gate |
| risk_tier | low / standard / high / release |
| impact_scope | 待填写 |
| completed_at | 待填写 |
| changed_modules | 待填写 |
| acceptance_or_scenario_ids | none / 待填写 |
| evidence_manifests | none / `.agent-state/runs/<run_id>/manifest.json` |
| waivers | none / 待填写 |
| knowledge_promotion | promote / defer / none / already-promoted |
| next_task_or_follow_up | none / 待填写 |

## Recall Metadata (Optional)

Use this section only when it helps future history search. Omit the entire section when it is not useful. Keep it short and source-linked.

| field | value |
|---|---|
| event | one-sentence task/event description |
| entities | modules, systems, commands, validators, providers, or external services |
| source_refs | summary/evidence paths only; no raw logs or large artifacts |

## Summary

## Key Decisions

## Evidence Index

## Knowledge Promotion

## Boundaries
```

Optional summary metadata may include `commit_or_push`, `related_runs`, `commit_hash`, `event`, `entities`, or `source_refs` when useful. Do not make those optional fields a blocker for archive hygiene.

## Archive Rules

- Copy `task_plan.md`, `findings.md`, and `progress.md` into the archive for audit.
- Optional helper: run `.agents/scripts/create-task-archive.py --root . --task-id YYYYMMDD-short-slug --status completed --dry-run` to preview the archive, then rerun with `--apply` to write it. The helper only generates `summary.md` and copies the root three files; it does not clear root state, run closeout, read raw logs, or replace `validate-task-archive-hygiene.py`.
- Do not create a formal `.agents/tasks/<task-id>/` directory until `summary.md`, `task_plan.md`, `findings.md`, and `progress.md` are ready together. Use `.agent-state/tasks/archive-ready/<task-id>/` for staging.
- Keep `summary.md` short enough to be the default historical entry point.
- Do not put logs, traces, HAR files, screenshots, dependency caches, packages, DB dumps, generated release assets, or runtime data in `.agents/tasks/`.
- Put run evidence under `.agent-state/runs/<run_id>/` and reference its `manifest.json`.
- `evidence_manifests` must list `.agent-state/runs/<run_id>/manifest.json` entries only. Business reports, validator JSON, scan reports, screenshots, and other artifacts belong in `## Evidence Index` and may be linked from the run manifest; they must not replace the run manifest itself.
- Stable project facts belong in `.agents/references/*`, not in archive summaries.
- `next_task_or_follow_up` is reference-only; it is not a backlog, issue tracker, or active task instruction.
