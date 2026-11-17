# Proposal

## Why

The archived `rc-plan` design lists `hosted-observation` as Change 11 of the operation catalog
(A.11), in its family 5; the archived `rc-scope-plan` design puts it in the batch of 2026-11-28, and
DR-0029 keeps that batch. The owner decided on 2026-11-15 that the hosted reader is one reader that
reads both forges, and that it is gate work of 0.2.0-beta.12.

Three facts of 2026-11-15 are its acceptance:

- Five sessions run only on the forges: `external_links`, `host_conformance`,
  `hosted_verification`, `release_binary_scan` and `release_journey`. No gate of either registry
  runs them.
- A head passed its full proof of 34 gates, landed, and failed `host_conformance` on both forges
  within seconds, because a list of test names had no reader on the workstation. A later head
  failed one test on the forge first, for a link in a document that an installation carries.
- A landing does not ask whether its head has a hosted run. The release lane refuses by its own
  script, which keeps a list of the job names that may fail.

At the base the product claims no hosted state at all: `publish` reports
`hosted_ci_status_claimed: false`, and the one forge reader, in
`src/ethos/adapters/mutation/publication/retirement.py`, lists reviews and no runs.

## What Changes

- One reader returns the hosted runs of one exact commit on a CI peer, through the provider's own
  authenticated CLI. One reader holds two forge keys. The run's own conclusion decides the run: a
  run that passed is one row, and a run that failed or still runs lists its jobs that did not
  pass, a job that the pipeline lets fail told apart.
- `ethos publish --observe-hosted` reads every CI peer for the worktree's head and exits by its
  verdict: `pass` when each peer's runs passed, `block` for a failed run or a peer that holds no
  run, `unknown` for a run that has not concluded or a forge that gave no usable answer.
- Four registered gap codes name a peer that did not pass: `hosted_run_missing`,
  `hosted_run_failed`, `hosted_run_running` and `hosted_run_unknown`, each with its repair.
- The landing's preview states the same observation under `data.hosted_observation`. It refuses
  nothing for it.
- The probe of a release ref, the release branch or a release tag, states the observation of its
  proof head in the same way and refuses nothing for it.
- The requirement that a release ref needs a passing observation is not armed. DR-0029 lets a rule
  refuse only after a release that reported it, so the refusal arms no earlier than the release
  after this one, in a Change that also adds the stored record.
- Candidate, not built here: a failed observation job says what it observed. Read on
  2026-11-16: the external link job failed on five hosted runs, its log named no link, and only
  its uploaded report held the checker's diagnostic, so an allowed failure went unread for two
  days. The session prints the report's gaps to the job log, and the reader lists them beside
  the run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED `Hosted runs of one head are read on every CI peer`, `The
landing preview states the hosted observation` and `The probe of a release ref states the hosted
observation`.

## Impact

`src/ethos/adapters/mutation/publication/hosted_runs.py` (new) and `forge.py`, whose bounded
provider listing `retirement.py` now shares; `src/ethos/application/publication/hosted.py` (new)
and `operation.py`; `src/ethos/application/land/operation.py`;
`src/ethos/repository/release/publication.py`, which names the roles of a release ref; the catalog
and the `publish` and `land` operation contracts; the gap registry;
`docs/reference/command-plane.md`; `CHANGELOG.md`; their tests. The `publish` request gains one
field, `observe_hosted`, in the CLI, the SDK function and the MCP tool. `land.preview` gains the
effect `remote-read`. No refusal is added: a preview's and a probe's verdict and required gaps are
what they were.
