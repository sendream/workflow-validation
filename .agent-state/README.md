# Agent State

`.agent-state/` is the writable local runtime area for this workflow.

This directory is intentionally separate from `.agents/`, because `.agents/`
contains checked-in workflow rules, skills, templates, scripts, and references.
Runtime files must not be written into the protected control directory.

## Layout

- `.agent-state/flags/`: local hook flags, smoke markers, lock directories, and runtime status files.
- `.agent-state/runs/<run_id>/`: command logs, JSON summaries, screenshots, traces, and run manifests.
- `.agent-state/tasks/current/`: optional active-task scratch state; root `task_plan.md`, `findings.md`, and `progress.md` remain the source of truth.
- `.agent-state/tasks/archive-ready/`: fallback location when final handoff archives cannot be written to `.agents/tasks/`.

## Legacy Compatibility

Existing projects may still contain `.agents/state/` or `.agents/runs/`.
New workflow writes must use `.agent-state/`. Scripts may read the old paths for
compatibility, but should not create new runtime files there.

Compatibility precedence is fixed: current `.agent-state/...` first, matching
legacy `.agents/...` second. The two locations are never merged. If both exist,
the current path wins and the legacy value is ignored; if only the legacy path
exists, callers must surface that it is deprecated rather than treating it as a
fresh current fact.

For a bounded read-only lookup, use:

```bash
python3 .agents/scripts/state-compat.py \
  --current .agent-state/flags/example.enabled \
  --legacy .agents/state/example.enabled \
  --deprecated-since 2026-07-22 \
  --remove-after 2026-12-31 \
  --format json
```

`deprecated_since` and `remove_after` are migration metadata, not an automatic
deletion schedule. Do not remove legacy artifacts in the same change that adds
or migrates a reader.

### Dual-path inventory and migration window

Only the following compatibility reads are permitted. A reader must select one
path, record the origin when it exposes a result, and never combine flags or
evidence from the two locations.

| fact family | current path | legacy fallback | owner / precedence | migration state |
| --- | --- | --- | --- | --- |
| planning session catch-up opt-in | `.agent-state/flags/planning-session-catchup.enabled` | `.agents/state/planning-session-catchup.enabled` | `state_compat.py`; current-first | adapter migrated; legacy deprecated since 2026-07-22, earliest removal 2026-12-31 |
| planning strict Stop opt-in | `.agent-state/flags/planning-strict-stop.enabled` | `.agents/state/planning-strict-stop.enabled` | `state_compat.py`; current-first | adapter migrated; legacy deprecated since 2026-07-22, earliest removal 2026-12-31 |
| workflow smoke / dirty marker | `.agent-state/flags/workflow-smoke.last`, `.agent-state/flags/workflow-dirty.flag` | matching `.agents/state/` paths | `state-compat.py`; current-first when a current/legacy marker must be selected; clean fingerprint is independent | adapter migrated; legacy deprecated since 2026-07-22, earliest removal 2026-12-31; no legacy asset is deleted during the window |
| run evidence references | `.agent-state/runs/<run_id>/...` | `.agents/runs/<run_id>/...` | evidence validators accept legacy references only where their contract says so | read-only archive/migration compatibility; new evidence always uses current path |

`state-compat.py` is read-only. It cannot create a directory, migrate a file,
clear a flag, or authorize deletion. The clean hook fingerprint does not need a
dual-path decision and therefore avoids an adapter subprocess; whenever a
current/legacy marker is actually selected, the shared adapter is the only
precedence implementation.

`graphify-stale.flag` is written only to `.agent-state/flags/` by
`graphify-stale-check.sh`. A pre-existing legacy stale flag is neither read nor
deleted by that checker; it is not a routing or code-context fact.

## Rules

- Do not store secrets, cookies, tokens, HAR files, database exports, or production data here.
- Do not commit runtime contents. Keep only this README and `.gitignore`.
- Long stdout/stderr belongs under `.agent-state/runs/<run_id>/`; `progress.md` should only link to artifacts and summarize conclusions.
- Completed handoff archives still prefer `.agents/tasks/YYYYMMDD-short-slug/`; if that path is not writable, write or suggest `.agent-state/tasks/archive-ready/YYYYMMDD-short-slug/`.
- Full-profile trajectory hooks may write `.agent-state/flags/trajectory-monitor.json`. It is a volatile, digest-only rolling window: it stores no raw command, patch, prompt, path, or output; it is not evidence, authorization, task state, or a long-term observation ledger.
