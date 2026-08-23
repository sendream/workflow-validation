# Legacy Workflow Runs

`.agents/runs/` is kept only for legacy compatibility.

New run evidence must be written to `.agent-state/runs/<run_id>/` because
`.agents/` is the checked-in workflow control directory. `progress.md` may still
reference old artifacts from this directory during migration, but new scripts
must not create new run output here.

Rules:
- `progress.md` only links to key artifact paths and conclusions.
- Do not store secrets, cookies, tokens, HAR files, database exports, or production data.
- Completed handoff archives belong in `.agents/tasks/` or, if that is not writable, `.agent-state/tasks/archive-ready/`.
