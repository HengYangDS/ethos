# Tasks

## 1. Identity

- [x] 1.1 Name the host conformance job from its matrix coordinates and regenerate the GitHub projection. Done when `ethos lane project` reports the projections current and the job is named `${{ matrix.os }} / Python ${{ matrix.python }}`.
- [x] 1.2 State the identity as a regression: each projected job's name is a function of its matrix coordinates on both forges. Done when `tests/architecture/ci/test_job_identity.py` passes and failed before the rename.

## 2. Spec And Record

- [x] 2.1 Add the quality requirement that hosted check names are stable identities. Done when strict validation passes and the simulated archive leaves every spec valid (12 specs valid after the simulated archive).
- [x] 2.2 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Archive, prove once, land and publish `dev` to GitHub; confirm on the hosted run that the nine `<os> / Python <v>` checks report.
