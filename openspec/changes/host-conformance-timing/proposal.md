# Proposal

## Why

The host conformance job runs the package acceptance (`nox -s host_conformance`) on every hosted
platform. The acceptance writes the timing of each of its stages to
`build/evidence/local-install/smoke.events.jsonl` beside its receipt `smoke.json`, and the receipt
names that file as its `execution_events`. Both hosted projections upload only `smoke.json`, which
carries no durations.

- On 11-03 the `windows-11-arm` leg of GitHub run 41588903580 took 75.4 minutes, 69.8 of them in
  the package acceptance, against 26.4 minutes for the same step on `windows-latest`. Which stages
  take that time under x64 emulation cannot be read from the uploaded artifacts, and the owner's
  decision on that leg waits for it.

## What Changes

- The GitHub and GitLab host conformance jobs upload `smoke.events.jsonl` with `smoke.json`, also
  when the job fails.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: hosted host conformance retains the stage timings of its package acceptance.

## Impact

The host conformance jobs in `.config/ci/pipeline.cue`, the generated `.github/workflows/ci.yml`
and `.gitlab-ci.yml`, an architecture test and the changelog. What the jobs run does not change.
