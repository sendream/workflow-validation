# T3 `#5270` raw evidence bundle

This directory is the review package for fable5's raw-evidence audit of branch
`trial/t3-5270`. It supplements, but does not replace,
[`../t3-5270-report.md`](../t3-5270-report.md) and
[`../t3-5270-stats.json`](../t3-5270-stats.json).

## Binding disposition

- Task base: `868d4efdbcaf4c29387a99ba854be406b1a1ec99`.
- Last rejected candidate: `1ff34455be35812ab10cebd66e6730f68eab1196`.
- Product-reversion commit: `1ac5227a7c7f326867162751e5d80cbe9666fe90`.
- Report commit before this bundle: `fb0e0fee1292857e2920390e0b7d87d57dcee715`.
- Outcome: partial investigation only. No formatter fix is approved or present in
  the final tree.
- Final product diff against the task base is empty. The experimental commits
  remain in branch history and are explicitly reverted.

A `pass` status in an individual run means only that its command succeeded on
that candidate. It does not override a later blocking reviewer result. The
authoritative final review result is
[`raw/runs/t3-5270/role-review/qa/role-review-result.json`](raw/runs/t3-5270/role-review/qa/role-review-result.json),
and its strict contract validation is captured under
[`raw/runs/t3-5270-final-review-result-validation/`](raw/runs/t3-5270-final-review-result-validation/).

## Included records

- `state/`: the final ignored `task_plan.md`, `findings.md`, and `progress.md`.
- `raw/runs/t3-5270/`: baseline/candidate JSON, generated output, fixture
  manifests, evidence scripts, and all four Role Review packets/results.
- `raw/runs/t3-5270-*`: every task-prefixed captured run present at packaging
  time, including expected RED, candidate GREEN, full suites, differential
  probes, G20, and obsolete closeout evidence.
- `flags/`: bounded hook/monitor state snapshot supporting the reported single
  busy-skip and zero trajectory warnings.
- `controller-probes/`: the controller stdout that was not written by the run
  capture helper, with its evidence limitation stated alongside it.
- `external-comparison.md`: identities of the two post-lock upstream PR diff
  snapshots. Third-party diff bodies are not duplicated in this repository.
- `SHA256SUMS`: hashes for every bundled file except the checksum file itself.

The run directories and state files were copied byte-for-byte from the ignored
local task records. They were not normalized or rewritten for publication.

## Candidate/reviewer map

| candidate | review evidence | disposition |
|---|---|---|
| `d522def` | `raw/runs/t3-5270/role-review/qa-d522def/` | blocked: annotated-assignment drift, weak work bound, duplicate corpus-key collapse |
| `5757101` | `raw/runs/t3-5270/role-review/qa-5757101/` | blocked: CJK STRING drift and missing guard oracle |
| `4af4863` | `raw/runs/t3-5270-wide-name-{red,green}/` | controller-blocked before completed review: wide NAME drift |
| `483b25d` | `raw/runs/t3-5270/role-review/qa-483b25d/` | blocked: optional RHS-parenthesis boundary and inadequate matrix |
| `1ff3445` | `raw/runs/t3-5270/role-review/qa/` | blocked: prior base-spelling case remained open; 53/490 accepted surrounding-context mismatches |
| final `1ac5227` product state | `raw/runs/t3-5270-final-reverted-suite/` | safe baseline restored; 481 passed / 3 skipped |

## Known evidence hazards

1. `raw/runs/t3-5270-closeout/` predates the first blocking review. It is
   intentionally retained as stale evidence and must not be used as final
   closeout proof.
2. Candidate run names containing `final` mean “then-current candidate”, not an
   approved delivery revision.
3. `raw/runs/t3-5270-line-length-context-scan-green/` has a misleading legacy
   name. Its manifest exits nonzero and its stdout records remaining
   mismatches; it is negative evidence.
4. The first `qa-d522def/role-review-result-original.json` is the reviewer's
   schema-invalid initial result. The sibling `role-review-result.json` is the
   corrected result used for disposition.
5. `raw/runs/t3-5270/role-review/qa/packet-validator.json` is a pre-start packet
   validation with `require_result=false`. Use the separately captured strict
   final-result validation for the final contract claim.
6. The 625-case controller probe was emitted by an interactive tool call rather
   than the capture helper. Only its exact returned stdout was retained; the
   command body was not. It is corroborating stop evidence, not the sole basis
   for rejection. The strict reviewer probe and captured 6,020-case scan remain
   independently inspectable.

## Privacy and integrity review

- The source was the public Black checkout plus generated workflow evidence.
- A fixed-pattern scan found no private-key header, bearer credential,
  API/access token assignment, or password assignment in the included task
  records.
- No `.env` file, private key, unredacted external trace, or Codex Home content
  is included.
- Local absolute paths are retained because this is a raw bundle and the same
  paths were already present in the published trial report. They convey no
  credential.
- Runtime manifests may retain `redaction_status: unknown`; this is capture-tool
  metadata, not a claim that secrets were found. The publication scan above is
  independently rerun before commit.
- `SHA256SUMS` binds the exact review copy. Verify from this directory with
  `sha256sum -c SHA256SUMS`.

## Suggested fable5 audit sequence

1. Verify `SHA256SUMS` and the evidence inventory.
2. Confirm `868d4ef..HEAD -- CHANGES.md src tests` is empty.
3. Inspect the four reviewer result files and validate that each blocking claim
   has direct, replayable evidence.
4. Compare baseline/candidate benchmark JSON and generated output manifests.
5. Inspect the duplicate-preserving fixture manifests and the corrected
   comparator script.
6. Confirm later probes expand dimensions omitted by earlier GREEN matrices.
7. Confirm the final reverted-suite run is green and that no candidate PASS is
   presented as final approval.

The audit question is not “did any candidate run fast?” It is: did the workflow
correctly refuse delivery after direct evidence showed that the fast path could
change Black's formatted bytes?
