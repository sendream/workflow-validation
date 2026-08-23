# Post-lock upstream comparison inputs

The following upstream PR diffs were fetched only after independent candidate
`d522def` had locked. Their bodies are canonical third-party artifacts and are
not duplicated in this evidence bundle.

| PR | local fetched-diff SHA-256 | use in trial |
|---|---|---|
| `psf/black#5275` | `5c376c82fae90767464b77a9b7bc84390a0b98d2c72279a466899e7126adf5ea` | applied in a clean scratch worktree; required outputs matched but the frozen-base benchmark did not improve |
| `psf/black#5305` | `d89de7c667ead65b54e222e1cdf40ff3212758ae86e704b61a87550d4bd096c1` | locally adapted concept remained quadratic and changed one preview fixture |

These hashes identify the snapshots used for the comparison. They do not make
upstream code part of this branch's deliverable.
