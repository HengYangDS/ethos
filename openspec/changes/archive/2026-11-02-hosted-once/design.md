# Design

## Context

See [proposal.md](proposal.md). The GitHub workflow is projected from `.config/ci/pipeline.cue`
by `ethos lane project`; the projection policy allows exactly one workflow for each provider
(`tools/ci/ci_projection.py`, `provider_entry`). Its push trigger lists `dev`, `main` and
`proposal/**`, and every commit-scoped job runs when `regularRun` holds, that is, outside the
supply-image and release dispatches. The quality gates admit the pushed range in their first step.

The repository ruleset protects `dev` and `main` and requires twelve of those jobs as status
checks; the owner's publication bypasses it, and a non-owner push to `main` still needs those
checks to have passed on the pushed commit. `main` moves only to the exact accepted commit
(repository-governance "Independent release selection preserves accepted source" and the accepted
mirror scenarios of "Release tags preserve native product version authority").

## Goals / Non-Goals

**Goals:**

- One full GitHub run per published commit: `dev`'s, 305.8 to 324.8 job-minutes in the runs of
  11-02 and 11-03, against D11's 320.
- Every pushed ref keeps its hosted commit-range admission (adapters "Local pre-push is
  bypassed").

**Non-Goals:**

- Proposal runs. A lane's proposal run verifies its last code commit before landing; the commit
  that lands differs by the archived Change.
- Fewer job-minutes inside one run. Windows on Arm (about 72 minutes under x64 emulation) and the
  three Windows legs (about 40 each) dominate it; `platform-matrix` owns the matrix.
- Run selection in hosted observation. `tools/ci/hosted_observation.py` reads the latest run of
  the repository, so after a landing it reads the `main` admission run, as it already reads
  GitLab's commit-policy-only `main` pipeline; `fleet-status` owns reading runs by commit (FT2).

## Decisions

- **Skip on the event, not on a comparison.** GitHub has no counterpart of GitLab's
  `compare_to`, and a job condition cannot read another branch. The commit-scoped jobs run unless
  the event is a push to `main`. A tree comparison in a preceding job would need a `needs` edge and
  a status function on every commit-scoped job for a case the promotion rule already excludes.
- **Keep `main` in the push trigger.** Dropping it would remove the hosted admission of `main`
  pushes, which the adapters requirement keeps on both Forges.
- **Admit in a separate job.** A `commit policy` job runs only for a `main` push and reuses the
  Python bootstrap (about 33 seconds in the quality gates at `424d32538`) and the admission
  command the quality gates run. Leaving the admission in the quality gates would report
  `quality gates` as passed without running them.

## Risks / Trade-offs

- [The `main` run reports the skipped jobs as passed] → GitHub counts a job skipped by its
  condition as successful, also for a required check, so the commit can show those checks as
  passed while `dev`'s run of it is still running. The release dispatch already skips them the same
  way. Hosted verification is read from `dev`'s run of the commit, and no ETHOS admission reads
  GitHub check results.
- [A `main` commit that `dev` never received] → It would get no GitHub verification. Promotion
  refuses such a move, the ruleset requires the twelve checks for every push that does not bypass
  it, and GitLab still verifies a `main` tree that differs from `dev`.
- [Publication order] → If `main` reached GitHub at a commit whose `dev` publication failed, that
  commit would have no full GitHub run until `dev` is published.
