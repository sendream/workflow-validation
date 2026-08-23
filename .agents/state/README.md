# Legacy Workflow State

`.agents/state/` is a legacy compatibility location.

New runtime writes must use `.agent-state/flags/`, because `.agents/` is the
checked-in workflow control directory. Scripts may read old flags from this
directory during migration, but should not create new runtime files here.

Current flag names are unchanged:
- `workflow-smoke.last`
- `latest-smoke.log`
- `workflow-dirty.flag`
- `graphify-stale.flag`
- `graphify-stale.last`
- `planning-session-catchup.enabled`
- `planning-strict-stop.enabled`
- `sensitive-guard-strict.enabled`
- `planning-reminder.last`
- `workflow.lock`
