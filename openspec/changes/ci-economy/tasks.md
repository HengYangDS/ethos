# Tasks

## 1. Model and projections

- [ ] 1.1 Move commit-range admission into `commit-policy` for every push and pull request, and
      replace the two placeholder jobs by `hosted checks`. Done when `lane project --check` passes
      and each push or pull-request event has one admission step.
- [ ] 1.2 Key host conformance by platform id in three tiers, with the `qualify_head` and
      `windows_legs` inputs and the drift schedule. Done when a push selects four legs and a
      qualification ten.
- [ ] 1.3 Give GitLab its roles by event and the batch-head workflow rules. Done when a `dev` or
      proposal push projects commit policy and conformance only.
- [ ] 1.4 Bound every job: unpersisted checkout credentials, the timeout table with its compile-time
      check, and cancellation for pull and merge requests. Done when a gate timeout at or above its
      class's minutes fails compilation.

## 2. Measurement

- [ ] 2.1 Read at least 100 runs per job class from both Forges, first attempt to final conclusion
      with a capacity cancellation counted as a failure, and replace each provisional value of
      `timeoutMinutes` by its class's p99 with margin. Done when the table's comment cites the
      read's date and n. Depends on forge read authority.

## 3. Caches, lockfile and runner tags

- [ ] 3.1 Add lock-keyed restore steps to the verification jobs and save steps to the scheduled run,
      with `actions/cache` pinned to its latest stable commit and the pinned `setup-uv`'s own cache
      turned off. Done when no release job has a cache step and only the schedule event saves. Needs
      network.
- [ ] 3.2 Generate and commit `actions.lock` and add its offline regression. Done when every `uses`
      pin has a lock entry and the paradigm admits the file's place. Needs network.
- [ ] 3.3 Take the runner tag of `dev` and `main` pipelines from a protected variable. Done when a
      protected ref's jobs name that tag. Depends on the owner's read-back of the variable.

## 4. Tests and guide

- [ ] 4.1 Update the architecture tests that pin the projections and add
      `tests/architecture/ci/test_hosted_economy.py`. Done when they pass and tests grow by at most
      60 line-equivalents.
- [ ] 4.2 Require both batch-head runs in step 4 of the release guide. Done when the guide names
      `qualify_head` and `ETHOS_QUALIFY_HEAD`.
- [ ] 4.3 Replace the three redirecting URLs in `docs/research/foundations/hosted-ci.md` by their
      targets. Done when the external link gate passes on the tree with no redirect hint.

## 5. Validation on the pushed proposal ref

- [ ] 5.1 Push the lane head. Done when GitHub's run passes with commit policy, four conformance
      legs, quality gates, link health and `hosted checks` and no Windows leg, and GitLab's pipeline
      passes with commit policy, host conformance and npm only.
- [ ] 5.2 Qualify the head. Done when a dispatch with `qualify_head` at the head runs ten legs, a
      dispatch with another head runs no commit-scoped job and fails `hosted checks`, a GitLab `api`
      pipeline with the head runs the full set, and one with another head is not created.
- [ ] 5.3 Read one run whose link observation failed. Done when it reports `hosted checks`
      successful and the run's conclusion successful.

## 6. Acceptance

- [ ] 6.1 Pass the static precheck and readiness at the lane head. Done when both pass with product
      and tools unchanged and tests at most 60 line-equivalents above the lane base.

## Workflow follow-up

- Owner: after `hosted checks` has reported once on `dev`, switch the ruleset's required checks to
  it and keep the previous list. Read back with
  `gh api repos/<owner>/<repo>/rulesets/<id> --jq .rules`.
- Owner: confirm the drift schedule (Saturday 19:00 UTC, provisional) and create GitLab's weekly
  schedule on `dev`. Read back with `gh run list --workflow "ETHOS CI" --event schedule --limit 3`
  and `glab api projects/:id/pipeline_schedules`.
- Owner: set the Require-lockfile policy. Read back with
  `gh api repos/<owner>/<repo>/actions/permissions`, or with a dated manual read if the field is
  absent.
- Owner: GitLab prerequisites. The role that may pass a pipeline variable
  (`glab api projects/:id --jq .ci_pipeline_variables_minimum_override_role`), a runner maximum
  timeout of 130 minutes or more (`glab api runners/<id> --jq .maximum_timeout`) and the protected
  tag variable (`glab api projects/:id/variables --jq '.[].key'`, keys only).
- Delivery: ten `dev`-push medians within target, capacity per runner class, and the first cache
  that the schedule writes (`gh cache list --ref refs/heads/main`).
