# Validation Coverage Map

Owner: workflow maintainers
Refresh when: a smoke assertion, behavior expectation, closeout child validator, or full runtime invocation changes.

This is a **reference-only ownership map**, not a runner, state source, delivery gate, or authorization surface. It separates the named validation layers so a failure has one primary diagnostic route. A secondary defense may still run during migration or at a different lifecycle point; it never changes the primary owner.

`package-contract` is the default aggregate of two independently runnable slices: `package-preflight` (installed files, absences, syntax, JSON, executable bits, size budgets) and `product-oracles` (declarative product contracts and bounded helper fixtures). Existing CI keeps the aggregate. Later mechanism retirements should edit `product-oracles`, not hostage preflight. `deterministic-behavior` protects fixture-driven selector/router/parser/validator semantics. `runtime-smoke` protects an applied full overlay and hook protocol. `closeout-bundle` remains a focused fact-domain orchestrator rather than a fourth general smoke layer.

## Failure-mode ownership

| id | critical | failure_mode | current_commands | route_profile | positive_case | negative_case | primary_owner | secondary_defense |
|---|---|---|---|---|---|---|---|---|
| VC-PC-REQUIRED-FILES | yes | A required base overlay asset is absent. | `verify-workflow-smoke.sh --layer package-contract` | base | Starter pack contains each required asset. | Remove one required asset in a temporary fixture. | package-contract | none |
| VC-PC-DECLARATIVE-CONTRACT | yes | A required marker, template field, link target, or declarative policy contract drifts. | `verify-workflow-smoke.sh --layer package-contract` | base | Source declarations match the frozen contract. | Mutate a required marker or reference in a temporary fixture. | package-contract | legacy-secondary-behavior |
| VC-PC-SYNTAX-AND-JSON | yes | A packaged script or hooks manifest cannot be parsed. | `verify-workflow-smoke.sh --layer package-contract` | base | Shell, Python, and JSON syntax parse. | Supply malformed syntax or JSON fixture. | package-contract | runtime-smoke |
| VC-DB-CONTEXT-ROUTING | yes | Prompt evidence, explicit task state, or budget fields produce an unsafe or ambiguous selector result. | `run-workflow-evals.sh --layer deterministic-behavior` | base | Explicit routing wins and evidence remains visible. | Negated release/external wording or conflicting state fixture. | deterministic-behavior | legacy-secondary-behavior |
| VC-DB-PARSER-AND-VALIDATOR | yes | A shared parser or fact-domain validator accepts malformed state or hides its error. | `run-workflow-evals.sh --layer deterministic-behavior` | base | Valid fixture returns structured pass. | Contradictory task state or malformed validator fixture fails with its fact-domain error. | deterministic-behavior | package-contract |
| VC-DB-OWNERSHIP-MAP | yes | A critical failure mode has zero, invalid, or multiple primary owners, or a frozen source surface changed without review. | `run-workflow-evals.sh --layer deterministic-behavior` | base | Map has one valid owner and matching source inventory. | Mutate a primary owner or source assertion without refreshing the inventory. | deterministic-behavior | none |
| VC-DB-STATE-COMPATIBILITY | yes | Current and legacy local markers disagree and a reader merges or gives legacy state priority. | `run-workflow-evals.sh --layer deterministic-behavior` | base/full | Current marker is selected with an observable `origin=current`. | Conflicting current/legacy fixture selects legacy or merges flags. | deterministic-behavior | package-contract |
| VC-DB-CAPABILITY-ADMISSION | yes | A malformed capability card is accepted, or a valid card changes capability permissions by itself. | `run-workflow-evals.sh --layer deterministic-behavior` | explicit capability trial | Valid read-only card is report-only admission metadata. | Missing approval, untrusted authority, secrets scope, or unrecoverable write declaration fails. | deterministic-behavior | package-contract |
| VC-DB-MEASUREMENT-PROMOTION | yes | A workflow cost result promotes a candidate without per-route, configuration-bound, correctly scoped measurement. | `workflow-value-report.py --measurement-result <explicit-result>` | explicit evolution only | Measured all-agent/single-agent total with target, negative, and regression routes is eligible only for a separate decision. | Root-thread mislabeled as all-agent, estimated bytes labeled measured token, missing config digest, regression route, or preregistered control binding is rejected. | deterministic-behavior | none |
| VC-DB-HOOK-PRESET-BOUNDARY | yes | Assist retains high-frequency lifecycle hooks, or clean Stop scans unrelated source roots / persists raw payload. | `run-workflow-evals.sh --layer deterministic-behavior` | full/assist | Assist has only bounded orientation/guard events; clean fingerprint skips Graphify. | Source-root scan sentinel or raw payload appears in telemetry fixture. | deterministic-behavior | runtime-smoke |
| VC-RT-APPLIED-OVERLAY | yes | Full-profile assets fail after application even though source files look valid. | `verify-workflow-smoke-full.sh --layer runtime-smoke` | full | Temporary full overlay initializes and passes. | Omit or stale-fork an applied base smoke asset. | runtime-smoke | package-contract |
| VC-RT-HOOK-PROTOCOL | yes | A lifecycle hook blocks on stdin, mishandles malformed Stop payload, or loses its fast-path safety behavior. | `verify-workflow-smoke-full.sh --layer runtime-smoke` | full | PTY and hook fixture paths return bounded valid output. | Held-open stdin, malformed payload, busy or stale lock fixture. | runtime-smoke | deterministic-behavior |
| VC-RT-INSTALLATION-BOUNDARY | yes | Full runtime smoke silently re-runs the broad base audit or claims full governance merely from installation. | `verify-workflow-smoke-full.sh --layer runtime-smoke` | full | Runtime uses only a bounded installation preflight when it needs a base precondition. | Fixture with stale base marker or an unexpected full static audit call. | runtime-smoke | none |
| VC-CLOSEOUT-FACT-DOMAINS | yes | Closeout skips, repeats, or conflates a release, reviewer, waiver, trace, or evidence fact domain. | `validate-task-closeout.py --format json` | high-release-closeout | Each triggered fact-domain validator runs once with its own result. | Trigger a malformed fact domain and verify its named error remains visible. | closeout-bundle | deterministic-behavior |
| VC-CLOSEOUT-SNAPSHOT-CONFLICT | yes | Root task state disagrees and closeout silently chooses an arbitrary task identifier or lifecycle. | `validate-task-closeout.py --format json` | high-release-closeout | Complete shared snapshot agrees with root files. | Contradictory or partial root-state fixture fails closed. | closeout-bundle | deterministic-behavior |
| VC-LEGACY-SECONDARY-BEHAVIOR | no | A retained shell fixture disagrees with the deterministic primary suite during a time-bounded compatibility audit. | `run-workflow-evals.sh --layer deterministic-behavior --include-legacy-shell-secondary` | explicit-compatibility | Explicit compatibility audit remains green. | Intentionally malformed legacy fixture reports a labeled source-smoke failure. | deterministic-behavior | legacy-shell-secondary |

## Frozen source inventory

The table freezes every existing assertion surface by normalized source-line count and SHA-256 digest. This is intentionally more maintainable than copying 1,000+ assertion rows into Markdown: a changed individual invocation changes the count or digest, and the deterministic ownership check requires an explicit map refresh. `selector` is a regular expression applied line-by-line to the listed source file.

| inventory_id | source | selector | count | sha256 | primary_owner |
|---|---|---|---|---|---|
| base-require-file | .agents/scripts/verify-workflow-smoke.sh | ^require_file " | 116 | 05e783a6a65292728a9c3ebd6a5c173117b67468e9f6af8053172a3fa3009fe4 | package-contract |
| base-require-absent-file | .agents/scripts/verify-workflow-smoke.sh | ^require_absent_file " | 19 | e9a347fa1210ce922219fabf73aceae3128665f8916c77cb8c337172d45c6a61 | package-contract |
| base-require-absent-dir | .agents/scripts/verify-workflow-smoke.sh | ^require_absent_dir " | 5 | e276cf07e7cdeb0a8e39c15a291e2621e6256a862827b8c5ae8c59cae44883de | package-contract |
| base-require-contains | .agents/scripts/verify-workflow-smoke.sh | ^require_contains " | 96 | ee339798902a02d1e4c8f149733423bf1a2507725f7e68b6cdc3cb966e06fff1 | package-contract |
| base-require-not-contains | .agents/scripts/verify-workflow-smoke.sh | ^require_not_contains " | 9 | 7efcc8c95c7457d0be6e84b45145c2826614821b294020eb02b69d006c11df4e | package-contract |
| base-require-git-or-local-exclude-contains | .agents/scripts/verify-workflow-smoke.sh | ^require_git_or_local_exclude_contains " | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | package-contract |
| behavior-fixture-definitions | .agents/evals/behavior/run_behavior_evals.py | ^def [A-Za-z0-9_]*fixture | 115 | b34a1d1f32f155c38a92a955889789331eacbffc4dd484b244b3b19fd5b41151 | deterministic-behavior |
| behavior-expectations | .agents/evals/behavior/run_behavior_evals.py | ^\s*failures \+= expect\( | 461 | 5d6d9aef8b2c2ffa5302d2f6597bc43b6585ad1f91a40a576ad61d8f04c888fc | deterministic-behavior |
| legacy-shell-secondary-runner | .agents/scripts/run-workflow-evals.sh | .+ | 1686 | 3232e895cb2ceba8fd66b7a19e1e93fdf65687c3488c4c80dc11ffcfd75c8e69 | deterministic-behavior |
| closeout-child-validator-invocations | .agents/scripts/validate-task-closeout.py | str\(scripts / "validate-[^"]+\.py"\) | 13 | f87fc2afde15284c6adaf038214dc41f4665de4a49f6906dfc2d8ba164646450 | closeout-bundle |
| full-smoke-script-invocations | profiles/full/project/.agents/scripts/verify-workflow-smoke-full.sh | \$ROOT/\.agents/scripts/[A-Za-z0-9_.-]+ | 21 | 3f2b5068d0340686201845141ac859b4efd051c7516b8bf06df94b90a6fd8135 | runtime-smoke |
| full-template-task-plan-structure | .agents/templates/task_plan.md | h2-or-table-header | 56 | b02d49714cbba7a666996454723efae26f8f137c2a4f76e07931e26fb5a9edc3 | deterministic-behavior |
| full-template-findings-structure | .agents/templates/findings.md | h2-or-table-header | 20 | 9cc421a62012e0600678afcfe3a56c746586351d386ca5ec88820399da1850a7 | deterministic-behavior |
| full-template-progress-structure | .agents/templates/progress.md | h2-or-table-header | 94 | 268b5963198258d0edb59c84026450a79943c817ce6a5584472d18ffc6512a31 | deterministic-behavior |

## Layer commands

| layer | command | scope boundary |
|---|---|---|
| package-contract | `.agents/scripts/verify-workflow-smoke.sh --layer package-contract` | Default aggregate of package-preflight then product-oracles. Does not own applied-full hook behavior. |
| package-preflight | `.agents/scripts/verify-workflow-smoke.sh --layer package-preflight` | Installed-file, absence, syntax, JSON, executable, and size-budget slice. Does not own product string contracts. |
| product-oracles | `.agents/scripts/verify-workflow-smoke.sh --layer product-oracles` | Declarative product contracts and bounded helper fixtures. Edit here when a mechanism retires. |
| deterministic-behavior | `.agents/scripts/run-workflow-evals.sh --layer deterministic-behavior` | Does not install a full overlay or infer hook runtime timing. |
| runtime-smoke | `.agents/scripts/verify-workflow-smoke-full.sh --layer runtime-smoke` | Does not re-run the full static package audit. |
| closeout-bundle | `.agents/scripts/validate-task-closeout.py --format json` | Runs only triggered fact domains; it is not a general smoke runner. |

## Change protocol

1. Add or move a check only after assigning its independent failure mode to one primary owner.
2. Keep any duplicate check as a named secondary defense with a reason and retirement trigger; do not describe it as a second primary owner.
3. Refresh the frozen inventory only in the same change that updates its coverage or ownership.
4. Run the positive ownership test and an invalid-owner negative fixture through deterministic behavior before relying on the map.
