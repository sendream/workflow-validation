# workflow-validation

This repository is a review-only snapshot for Black trial run 1. It is based on the
unchanged upstream Black revision `8947c48ef2077c3a301b03c1e814dc2e3f78436e`.

## Review range

- Base: `8947c48ef2077c3a301b03c1e814dc2e3f78436e`
- Commit 1: installed full workflow overlay and filled minimal Black project knowledge
- Commit 2: T0 color-test environment isolation plus the Step 1 evidence report

Review the complete candidate with:

```bash
git diff --stat 8947c48ef2077c3a301b03c1e814dc2e3f78436e..HEAD
git diff 8947c48ef2077c3a301b03c1e814dc2e3f78436e..HEAD -- tests/test_black.py
```

## Intentional boundary exception

The installed overlay is normally local-only and the G20 overlay-boundary validator
therefore rejects it when staged. The user explicitly authorized committing it to this
dedicated validation repository so fable5 can inspect the exact installed state. It is
not a Black business deliverable and is not pushed to `psf/black`.

## Excluded machine state

- the external Python virtual environment;
- the duplicate bare comparison clone and both repositories' `.git` directories;
- Python bytecode, pytest caches and generated `src/_black_version.py`;
- `.agent-state/runs/` installer runtime data.

The excluded comparison clone remains fixed at the base SHA. Its state, environment,
commands, timings and results are recorded in
`trial-reports/step-1-baseline-report.md`.

## Replay

From a Python 3.12 virtual environment with the development and test dependencies:

```bash
env -u NO_COLOR python -m pytest -n auto
bash .agents/scripts/verify-workflow-smoke.sh
```

The submission contains no upstream push, pull, rebase or baseline refresh.
