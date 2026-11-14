# Tasks

## 1. Retention in the models

- [x] 1.1 Declare `artifactRetentionDays` in `.config/ci/pipeline.cue`, read it in every upload
      step's `with` and every GitLab `artifacts` block, and regenerate both projections. Done when
      the projection check reports no drift, the workflow holds seven `retention-days: 14`, the
      GitLab pipeline holds three `expire_in: 14 days`, and
      `tests/architecture/ci/test_gitlab_artifacts.py` passes after failing first.
- [x] 1.2 Declare the same retention in `.config/ci/verification.cue` and read it in the generated
      upload step and `artifacts` block. Done when
      `tests/unit/projection/test_verification_model.py` expects both keys on the generated jobs
      and passes after failing first.

## 2. Documents

- [x] 2.1 Add the CHANGELOG line and correct the model comment about the Python distributions.
      Done when the Markdown and prose gates pass on `CHANGELOG.md` and the model's format check
      passes.

## 3. Lane tasks

- [x] 3.1 Apply on the lane head after the Changes of this batch that edit
      `.config/ci/pipeline.cue`, regenerate the projections there with `ethos lane project`, and
      measure the three source budgets. Done when the projection check passes and the measured
      deltas are within +25 tests, 0 product and 0 tools, or the difference is recorded with its
      reason.
- [x] 3.2 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.

## 4. Hosted tasks

- [x] 4.1 State the expiry that each forge will show for an artifact of this Change. Done when the
      model and both projections carry the 14-day retention on every upload step and expiry key, as
      task 1.1 projects them.

## Workflow follow-up

- Artifacts uploaded before this Change keep their earlier retention. Deleting them is the owner's
  decision and a Forge action outside this Change.
- Each repository that compiles the common CI model regenerates its projections when it moves to
  the release that ships this Change.
- Delivery: after the first `dev` run and pipeline that carry this Change, read back one artifact of
  each
  (`gh api repos/<owner>/<repo>/actions/artifacts --jq '.artifacts[0] | {created_at, expires_at}'`;
  `glab api projects/:id/jobs/<id> --jq .artifacts_expire_at`) and record that each expires 14 days
  after its upload.
