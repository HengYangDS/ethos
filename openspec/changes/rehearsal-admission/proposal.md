# Proposal

## Why

`release-rehearsal` makes a release head's rehearsal a hosted run. Nothing in the product reads
it: a release tag is created and published whether its head was rehearsed or not, and DR-0026
asks, in its item on the release path, that tag admission require the rehearsal's receipt.

The archived `rc-plan` design gives the row in appendix B.1: an operation reads the newest
completed rehearsal of a head from the forge, a non-authorizing Attestation records it,
`land --release` refuses without it, and a repository opts in through its release binding. B.8
lists it as item 7, `rehearsal-admission`: B.1's observation, Attestation, opt-in and boundary
check; B.9 names the predicate and the configuration's owner. Family 7 orders the row as B7,
after `release-rehearsal` (B6) and the application package (A3), which is archived. The archived
`rc-scope-plan` design places the row in the batch of 0.2.0-beta.13, and DR-0029 records that
cutting the rehearsal and its admission was not taken.

Three facts shape what is built first:

- A rehearsal is a hosted run of one commit, and `hosted-observation` already reads the hosted
  runs of one commit through the forge's signed-in CLI, without storing them. A failed
  rehearsal therefore already makes its peer's observation `failed`. What no reader states is
  that a rehearsal exists.
- DR-0029's rule R14 lets a release refuse only what an earlier release reported, and its law
  freeze admits no new rule before 0.2.0 without a named exception.
- The plan's full form is estimated at 305 to 470 product and 610 to 940 test line-equivalents,
  against a planned 200 and 170. The first slice below is estimated at 100 to 155 product and
  200 to 310 test line-equivalents. The design states the measured neighbors that the
  estimates rest on.

## What Changes

- A release binding may name the peer that rehearses its releases:
  `[release.rehearsal] peer = "<peer>"`. A binding without the table is not read for a
  rehearsal and is refused nothing.
- One reader finds a head's rehearsal among its hosted runs on that peer: the newest dispatched
  run that ran the rehearsal's verdict job. That job's conclusion decides, so a newer failure is
  never outvoted by an older pass.
- `ethos publish --observe-hosted` states the rehearsal of the worktree's head, and the probe of
  a release tag states the rehearsal of the tagged head, under the hosted observation. Neither
  changes its verdict, its required gaps or its next action.
- One gap code, `release_rehearsal_unproven`, names a head whose rehearsal is missing, failed,
  running or unreadable. It is listed with the observation and is reported, not required: the
  rule enters in the reporting state.

Not breaking: no verdict changes. A binding that declares the table was refused by the paradigm
before, as a key that no reader consults; a valid table is now read.

Out of scope, and named for a successor Change: a stored record of the reading (the plan's
Attestation, under the predicate `release:rehearsal`), a command of its own, the refusal at
`land --release` or at the release tag's probe, and the product-boundary check that the product's
own binding keeps the table. The design states the successor's contract, and the owner names the
release that arms it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED `The hosted observation states a head's rehearsal` and `The
probe of a release tag reports its head's rehearsal`.
- `repository-paradigm`: ADDED `A release binding may name the peer that rehearses its
releases`.

## Impact

A new reader beside `src/ethos/adapters/mutation/publication/hosted_runs.py`;
`src/ethos/application/publication/hosted.py` and one argument in `operation.py`; the release
table's key set in `src/ethos/contracts/branch/roles.py` with its reader and the paradigm's
`release-binding` report; the gap registry; the paradigm's reporting list;
`docs/reference/command-plane.md`; `CHANGELOG.md`; their tests. No command, operation or request
field is added. A release tag's probe and an explicit observation make one more listing, and one
read of a run's jobs for each dispatched run they inspect, only where the binding opts in.
