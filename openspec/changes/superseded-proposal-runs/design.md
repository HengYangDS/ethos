# Design

## Context

See [proposal.md](proposal.md). `.config/ci/pipeline.cue` owns both Forge projections;
`tools/ci/ci_projection.py` generates `.github/workflows/ci.yml` and `.gitlab-ci.yml` from it, and
the `ci-projection` gate refuses drift. GitHub's workflow-level `concurrency` cancels the running
run of a group when `cancel-in-progress` is true, and its group expression may read the `github`
context. GitLab 19.5 lets a matching `workflow:rules` entry set `auto_cancel:on_new_commit` to
`interruptible`, which cancels only interruptible jobs, or to `none`.

## Goals / Non-Goals

**Goals:**

- A newer proposal push stops the verification of the head it replaces on both Forges.
- No run of `dev`, `main`, a release, a manual dispatch or a pull or merge request is ever
  cancelled or queued by another run.

**Non-Goals:**

- The shipped adopter model. Its GitLab verify jobs are interruptible for every ref under the
  default `conservative` mode, and its GitHub workflow has no concurrency group; giving adopters
  the same rule is a separate Change with its own adopter migration.
- Fewer job-minutes inside one run, which the Windows legs dominate.
- Reusing a proposal run for the landed `dev` commit, which needs `land` to read hosted results
  first.

## Decisions

- **One group per proposal ref, one group per run otherwise.** The group is the workflow and ref
  for a push whose ref starts with `refs/heads/proposal/`, and the workflow and run ID for every
  other event, with `cancel-in-progress: true`. A run-unique group can never hold a second run, so
  the setting cannot cancel or queue anything outside proposal pushes. Deciding by the event keeps
  a manual supply-image dispatch on a proposal ref safe from a push of the same ref.
- **The whole run, not single jobs.** The superseded run verifies a head that no longer exists on
  the ref, so none of its jobs is worth finishing.
- **GitLab decides per workflow rule.** The proposal rule sets `on_new_commit: interruptible`; the
  rules for `dev` and `main` and for merge requests set `none`, which also stops today's
  cancellation of a waiting `dev` pipeline. `default: interruptible: true` marks every job, since
  the rule, not the job, selects where cancellation applies.

## Risks / Trade-offs

- [A superseded proposal run's own range admission is cancelled] → The newer run admits the range
  from the replaced head, and the `dev` push that lands the commits admits their whole range. No
  landing reads a superseded proposal run, and proposal refs are not protected.
- [GitLab cancels nothing if the project setting is turned off] → Proposal pipelines then run to
  the end as today; the `none` rules keep `dev` and `main` safe either way.
