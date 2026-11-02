# Tasks

## 1. GitHub verifies a published commit once

- [x] 1.1 Run the commit-scoped GitHub jobs (host conformance, quality gates, external links,
      repository proof, package artifacts) unless the event is a push to `main`, and admit every
      `main` push's range in a `commit policy` job. Done when
      `tests/architecture/ci/test_github_commit_scope.py` passes against the projected
      `.github/workflows/ci.yml` and `ethos lane project --check` reports no drift.
      (Its six cases fail against the workflow at `24d9dd498` and pass on the projection; the 59
      CI projection, job identity and workflow cases pass; `lane project --check` conforming.)
- [x] 1.2 Record the change under Unreleased in `CHANGELOG.md`. Done when the docs gates pass.
      (`markdown_lint`, `prose` and `ci_templates` pass.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
- After landing, the first published commit's GitHub `main` run executes only `commit policy`, and
  its `dev` and `main` job-minutes are recorded against D11's 320.
