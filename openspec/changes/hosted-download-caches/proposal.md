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

The common CI model has the same gap for a governed repository: it generates no cache block for
either forge. The session that keeps the governed repositories reported on 2026-11-19, from the
job traces of one repository's latest successful pipeline, which were not read again here:
`mise install --locked` took 90 to 106 seconds in each of its three guest jobs, more than the
proof itself at 15 to 87 seconds. That repository's verification declaration keeps Mise's data
and cache under each job's own build directory, because a Windows runner could not write the
runner's shared profile, so every job downloads every tool. Other governed repositories, whose
jobs keep Mise's data in the guest's own store, bootstrap in 9 to 25 seconds.

## What Changes

- The requirement `Hosted download caches have one writer` returns with the cache steps.
- The unread artifact stops being uploaded, or gains its reader.
- Candidate, not decided: the common CI model can generate a job cache keyed by the tool lock and
  the platform, so that a repository with job-local tool data keeps its isolation and does not
  download every tool in every job.

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
