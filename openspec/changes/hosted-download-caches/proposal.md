# Proposal

## Why

`ci-economy` closed on its delivered scope. Its push runs met their targets without a download
cache: on GitHub 37.1 and 38.4 minutes against a target of about 40, and on GitLab 7.1 and 6.3
minutes against a target of less than a quarter of an hour. Four of its tasks left under DR-0016
and return here:

- Lock-keyed restore steps in the verification jobs, saved only by the scheduled run.
- `actions.lock` for the workflow's action pins, with its offline regression.
- The runner tag of protected pipelines from a protected variable, which waits for the owner's
  read-back.
- One run whose link observation failed, read to show that the run still concludes successfully. A
  `dev` run of 2026-11-15 is such a run.
- Not a task of that Change: every regular run uploads the `python-distributions` artifact and no
  job reads it.

## What Changes

- The requirement `Hosted download caches have one writer` returns with the cache steps.
- The unread artifact stops being uploaded, or gains its reader.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`.config/ci/pipeline.cue` and its two generated pipelines; the quality specification. Two push
runs are a point and no median.

Owner: the release lead. Next action: read ten `dev` push medians. Read again: when the ten
medians are read, or when a push run exceeds its target.
