# Tasks

## 1. Retention in the models

- [ ] 1.1 Declare `artifactRetentionDays` in `.config/ci/pipeline.cue`, read it in every upload
      step's `with` and every GitLab `artifacts` block, and regenerate both projections. Done when
      the projection check reports no drift, the workflow holds seven `retention-days: 14`, the
      GitLab pipeline holds three `expire_in: 14 days`, and
      `tests/architecture/ci/test_gitlab_artifacts.py` passes after failing first.
- [ ] 1.2 Declare the same retention in `.config/ci/verification.cue` and read it in the generated
      upload step and `artifacts` block. Done when
      `tests/unit/projection/test_verification_model.py` expects both keys on the generated jobs
      and passes after failing first.

## 2. Documents

- [ ] 2.1 Add the CHANGELOG line and correct the model comment about the Python distributions.
      Done when the Markdown and prose gates pass on `CHANGELOG.md` and the model's format check
      passes.

## 3. Lane tasks

- [ ] 3.1 Apply on the lane head after the Changes of this batch that edit
      `.config/ci/pipeline.cue`, regenerate the projections there with `ethos lane project`, and
      measure the three source budgets. Done when the projection check passes and the measured
      deltas are within +25 tests, 0 product and 0 tools, or the difference is recorded with its
      reason.
- [ ] 3.2 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.

## 4. Hosted tasks

- [ ] 4.1 After the first GitHub run and the first GitLab pipeline that follow this Change, read
      back one artifact of each. Done when each expires 14 days after its upload. Depends on forge
      read authority.

## Workflow follow-up

- Artifacts uploaded before this Change keep their earlier retention. Deleting them is the owner's
  decision and a Forge action outside this Change.
- Each repository that compiles the common CI model regenerates its projections when it moves to
  the release that ships this Change.
