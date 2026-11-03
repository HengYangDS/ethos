# Tasks

## 1. Journey

- [x] 1.1 Move the Mise installation of a declared ETHOS tool into `tools/ci/delivery/mise_tool.py`.
      Done when the distribution acceptance uses it and its tests pass.
- [x] 1.2 Add the journey and the `release_journey` Nox session. Done when its tests cover the
      previous release, the asset and attestation checks and the order of the journey's steps, and
      the new tests failed before the change.
- [x] 1.3 Add the `release-journey` job and the `journey_tag` dispatch input. Done when
      `ethos lane project --check` reports `conforming` and an architecture test checks the job's
      legs, dependencies and uploads.
- [x] 1.4 Record the change in the changelog. Done when the Unreleased section of `CHANGELOG.md`
      names it under Added.

## 2. Specification

- [x] 2.1 Write the `distribution` delta. Done when strict validation and the cumulative archive
      simulation pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass,
  and a `journey_tag` dispatch on the proposal qualifies a published prerelease.
- After landing, a `journey_tag` dispatch from `main` qualifies `v0.2.0-alpha.29`; its passing legs
  are the beta journey evidence, and the local `release-accept.sh` retires.
