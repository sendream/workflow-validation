# Progress Appendix: Human Decision Surface

> Snippet only. Copy into root `progress.md` when a derived report, gate, review, or risk assessment without a dedicated closeout section needs an explicit human decision. This is a closeout surface, not authorization, not a backlog, and not a second state source.
> Mechanisms with dedicated surfaces keep using those sections, for example `Skill Curator Closeout`; do not duplicate the same decision in two tables.

## Human Decision Surface
| decision_id | source | level | surfaced | default recommendation | options | disposition | authorization scope | evidence |
|---|---|---|---|---|---|---|---|---|
| not-needed / HD-YYYYMMDD-01 | workflow-value-report / release-source / review-boundary / requirement-reconciliation / external-skill / sensitive-operation / other-derived-report | record-only / surface-required / answer-required / risk-acceptance-required | not-needed / yes / asked-user / recorded / deferred / rejected / user-approved | conservative default; usually record-only, defer, narrow-trigger, or ask-user | A recommended option; B alternative; C stop/defer | record-only / ask-user:<question> / reject:<reason> / defer:<reason> / user-approved-scope:<scope> | none / repo-local / specific file paths / explicit user scope | `.agent-state/runs/<run_id>/...` / progress / findings |
