# Proposal

## Why

A Work Lane publishes its head as `proposal/<lane>` so that hosted CI verifies it before landing,
and GitHub runs the full verification, about 300 job-minutes, for every push of that ref. A newer
push of the same ref leaves the run of the earlier push running. On 11-03 the `ruff-docstrings`
lane pushed five heads in 82 minutes, and each of GitHub runs 41557986681, 41560219226,
41563907017 and 41565784290 kept running after a newer push had replaced its head, until it
finished: 1,225 job-minutes for heads that never landed. Over the five landings after `hosted-once`
(11-02 21:06 to 11-03 10:26 UTC) proposal runs took 3,317 of 5,058 job-minutes on both Forges.

GitLab cancels redundant pipelines for this project (`auto_cancel_pending_pipelines` is enabled)
in its default `conservative` mode, which cancels a pipeline only while none of its jobs that are
not interruptible has started. ETHOS's jobs are not interruptible, so a started proposal pipeline
runs to the end, while a `dev` pipeline that still waits for the runner is cancelled by a newer
`dev` push, although every `dev` push must be verified.

## What Changes

- GitHub: the workflow declares a concurrency group. A push of a proposal ref joins the group of
  that ref and cancels the in-progress run of its earlier push; every other event, including a
  manual dispatch on a proposal ref, has a group of its own, so no `dev`, `main`, release,
  supply-image, journey or pull-request run waits or is cancelled.
- GitLab: every job is interruptible; the workflow rule for proposal refs cancels the interruptible
  jobs of an earlier pipeline on a new commit, and the rules for `dev`, `main` and merge requests
  cancel nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a newer push of a proposal ref supersedes the run of its earlier push, and no newer
  event cancels a run of `dev`, `main`, a release or a pull or merge request.

## Impact

`.config/ci/pipeline.cue` with the generated `.github/workflows/ci.yml` and `.gitlab-ci.yml`, a
structural test in `tests/architecture/ci/`, and `CHANGELOG.md`. The shipped adopter CI model,
`.config/ci/verification.cue`, is unchanged.
