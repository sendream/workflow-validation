# Black Trial Run 1 — T2 `#5328` Workflow Comparison

- Recorded at: `2026-08-23T15:04:00+08:00`
- Outcome: `PASS — ready for fable5 review`
- Issue: `psf/black#5328`
- Frozen Black task baseline: `8947c48ef2077c3a301b03c1e814dc2e3f78436e`
- Frozen workflow source: `fe560cd54eb5c93f9473c0c3dd64c26e5e3fe7a9`
- Instrumented branch: `trial/t2-5328`
- Instrumented code commit: `e47994f766317f540cfa4cdc9ee03da4576afe38`
- Bare control commit: `5fb2b602c8f845744d19aa5ec47ca529a6b86b08`
- Upstream comparison was opened only after the instrumented code commit had locked the patch.

## 1. Task and route

The issue reproducer is a long parenthesized dictionary string followed by `# type: ignore`. Under `--unstable`, Black split the string, dropped the type-ignore comment, and then rejected its own output because the formatted AST had lost a `TypeIgnore` node.

The instrumented session classified this as `standard / visible` and used the bounded fast path. That matches the task card's estimated tier: the change is user-visible and requires a regression fixture and changelog entry, but it is confined to one existing transformation path and does not affect API, authorization, release, or external-system contracts. The fast path correctly did not create the three task-state files.

The instrumented branch starts from `868d4ef`, the review baseline containing Step 1 and T0. The bare control starts from the frozen upstream Black SHA `8947c48`. The only Black-code difference before T2 is T0's environment isolation in two color tests; it does not touch the formatter, long-string fixtures, or `CHANGES.md`, but it remains a minor experimental confound and is declared rather than hidden.

## 2. Instrumented arm

### RED and diagnosis

- Exact CLI reproduction: exit `123` with Black's non-equivalent-code INTERNAL ERROR.
- Fixture RED: `tests/test_format.py -k preview_long_strings__regression -q` failed because expected output retained `# type: ignore` while actual output lost it.
- Root cause: `StringParenWrapper` replaces an existing right parenthesis when it reconstructs the final line. Comments keyed to the old leaf were not migrated to the replacement leaf, so rendering omitted the pragma and the AST equivalence check lost its `TypeIgnore`.

### Fix

- `src/black/trans.py`: append comments attached to the old right parenthesis to the reconstructed closing line.
- `tests/data/cases/preview_long_strings__regression.py`: add the issue reproducer and literal expected output.
- `CHANGES.md`: add an Unreleased Preview-style entry because this is a user-visible crash fix.

### GREEN evidence

- Focused fixture: `1 passed, 235 deselected`.
- Exact CLI: exit `0`; the long string was split and `# type: ignore` remained present.
- Candidate-file pre-commit checks: Black revision/version check, isort, flake8, mypy, Prettier, EOF, and trailing-whitespace checks passed.
- Nested-session full suite: `481 passed, 3 skipped in 6.52s`.
- Independent full rerun: `481 passed, 3 skipped in 5.90s`, wall `9.65s`.
- `git diff HEAD^ HEAD --check`: pass.
- Code diff: 3 files, `+22/-1`.
- Production fix rework: zero.

## 3. Bare control arm

The control prompt contained only the issue facts, reproducer, acceptance criteria, NO_COLOR command, and upstream-contact prohibition. It did not mention either the instrumented patch or PR `#5329`, and the control checkout had no `AGENTS.md`, `.agents/`, or `.codex/` overlay.

The control independently found the same root cause and used the same three production lines. Its implementation places comment migration after trailing-comma reconstruction and adds a dedicated fixture file rather than extending the existing regression fixture.

- Exact CLI RED: exit `123`.
- Dedicated fixture RED: one failure because the pragma disappeared.
- Focused GREEN: dedicated fixture `1 passed`; the related long-string group `5 passed`.
- Nested-session full suite: `482 passed, 3 skipped in 6.07s`.
- Independent full rerun: `482 passed, 3 skipped in 5.97s`, wall `6.11s`.
- Exact CLI GREEN: exit `0`, comment retained.
- `git diff HEAD^ HEAD --check`: pass.
- Diff: 3 files, `+22/-0`.
- Production fix rework: zero.
- Operational rework: first commit attempt lacked Git identity; a command-local identity was used without changing repository or global configuration.
- Delegation: zero.

The control patch is preserved at `trial-reports/t2-5328/control.patch`; machine-readable measurements are in `trial-reports/t2-5328/stats.json`. The control branch and commit are local evidence only and are not pushed to `psf/black` or the review remote.

## 4. Measured comparison

Runtime usage below is the sum of the two `turn.completed` records in each Codex thread. Reasoning tokens are a reported subset of output accounting, not an additional total.

| Metric | Instrumented | Bare control | Instrumented delta |
|---|---:|---:|---:|
| Wall time | 882.80s | 431.27s | +451.53s / +104.70% |
| Input tokens | 5,759,094 | 2,575,486 | +3,183,608 / +123.61% |
| Cached input | 5,577,472 | 2,468,608 | +3,108,864 / +125.94% |
| Non-cached input | 181,622 | 106,878 | +74,744 / +69.93% |
| Output tokens | 27,665 | 15,109 | +12,556 / +83.10% |
| Reasoning output | 16,652 | 7,588 | +9,064 / +119.45% |
| Command executions | 48 | 92 | -44 |
| Mechanical delegations | 0 | 0 | 0 |
| Production-fix rework | 0 | 0 | 0 |

This single task does not show a success-rate advantage for the overlay: both arms independently reached a correct minimal fix in one production attempt. The instrumented arm used roughly twice the wall time and 2.24 times the input tokens despite issuing fewer shell commands. Most of the input increase was cached context, but non-cached input still rose by about 70%.

The control's extra test case explains `482` versus `481` passing tests: it created a new fixture file, while the instrumented arm added a case to an already enumerated fixture. It is not a product-behavior difference.

## 5. Workflow mechanisms actually consumed

### Useful

- Project knowledge supplied the correct acceptance command, `env -u NO_COLOR python -m pytest -n auto`; neither arm regressed into the already-adjudicated environment-sensitive path.
- The project conventions correctly required a `CHANGES.md` entry for this user-visible unstable-style crash fix.
- Routing selected the estimated standard tier while allowing a bounded fast path and avoiding unnecessary three-file state.
- G20 caused the instrumented arm to stage only the three task files and inspect the delivery boundary. The already-adjudicated linked-worktree false positive was handled once with independent `git check-ignore --no-index` evidence; no workflow file was modified.
- Local review separated code behavior, fixture oracle, changelog scope, and delivery hygiene before commit.

### Cost or friction

- The requirements-phase selector first modeled the task as complex and forecast `17,389/12,000` inferred tokens. A later fast selector reported no conditional reads and a `1,944/8,000` forecast, but the session nevertheless loaded 570 lines across context-memory, project conventions, common pitfalls, and verification evidence, then also read code-review and lifecycle material. This is the clearest source of avoidable context cost.
- An unscoped `pre-commit -a` scanned tracked local workflow material, reformatted several overlay/report files, and failed on unrelated overlay checks. All non-task changes were restored exactly before the candidate-file-only rerun. The failure did not escape into the commit, but it added wall time and context noise.
- The venv did not contain `pre-commit`, and an assumed `uvx` path was absent. The eventual `uv tool run --from pre-commit` path worked.
- Both arms encountered missing Git identity on their first commit attempt. This is trial-environment friction, not a workflow-arm effect.

### Guard, monitor, and state observations

- Edit guard warnings/blocks: `0`.
- Trajectory monitor warnings: `0`.
- G20 linked-worktree false positives: `1`, already covered by the standing ruling.
- Mechanical subagents: `0` in both arms; this task had one tightly coupled diagnostic/implementation stream, so non-delegation matches the activation guidance.
- `task_plan.md`, `progress.md`, and `findings.md`: the instrumented arm only checked existence; all were absent and none was read or written. This is appropriate for the bounded fast route.

The pre-commit incident is not classified as a missed edit-guard trigger: the changes were side effects of a Bash-invoked formatter, while the new edit guard covers official edit-tool patch events. It is instead evidence that repository-wide validation commands need candidate scope when the overlay itself is tracked in the review repository.

## 6. Post-lock comparison with upstream PR `#5329`

Only after commit `e47994f` locked the instrumented patch was `https://github.com/psf/black/pull/5329` opened.

At comparison time the PR was open and changed the same three logical surfaces with `+12/-0`:

- Production: the same three-line loop over `line.comments_after(old_rpar_leaf)` with `preformatted=True`.
- Placement: upstream puts the loop after optional trailing-comma reconstruction; the instrumented patch puts it immediately after appending the new right parenthesis. Under legal inputs on this path, a trailing inline comment after a comma belongs to the comma rather than the old right parenthesis, so targeted comma variants and the full suite exposed no behavior difference. The upstream/control placement more directly preserves final leaf order and is marginally clearer.
- Test: upstream adds only the issue input to the broad `comments6.py` fixture and relies on the fixture's normal idempotence/equivalence checks. The instrumented patch adds explicit input and expected output to an existing long-string regression fixture. The control creates a dedicated input/output fixture. Both local variants make the exact expected comment retention easier to inspect, at the cost of more fixture lines.
- Changelog: upstream includes `#5329`; the trial correctly omits a PR number because it must not create or claim an upstream PR.

The bare control independently matched the upstream production hunk byte-for-byte, including placement. The instrumented arm independently matched the underlying fix but not its exact location or fixture organization.

## 7. Trial disposition

T2 succeeds as a product fix and as a discriminating workflow trial:

- Both arms produced correct, minimal, independently derived patches with strict RED-to-GREEN evidence and full-suite confirmation.
- The overlay contributed accurate project-specific acceptance and delivery discipline but did not improve the observed implementation outcome on this bounded task.
- The overlay imposed substantial context and wall-time overhead. The strongest follow-up signal is not to remove evidence or routing gates, but to make the fast selector's empty conditional-read result operationally binding and to avoid whole-repository pre-commit scans in review-overlay trials.
- No source-workflow change is made during the frozen trial. These observations are report data for later source-repo adjudication.

No branch was pushed to `psf/black`, no upstream PR or issue comment was created, and the frozen workflow source remained unchanged.
