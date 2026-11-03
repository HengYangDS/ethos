# Tasks

## 1. Supply Pin

- [x] 1.1 Pin `jdx/mise-action` 5.2.6 by commit in `.config/ci/verification.cue` and record it in
      `CHANGELOG.md`. Done when no tracked file outside archived Changes names the 5.2.5 commit,
      `lane project --check` reports the projections conforming, and the verification model test
      passes. (Only archived Changes name `6612f0ef`; `lane project --check` reported `conforming`,
      and `tests/unit/projection/test_verification_model.py` passed 10 cases in 1.3 seconds.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
