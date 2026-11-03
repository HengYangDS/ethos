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
- [x] 1.5 Rehearse the journey locally on the published `v0.2.0-alpha.28` assets. The rehearsal
      skips the subject's attestation, which that release does not carry, and sets
      `ETHOS_PROOF_HOST_LOAD_LIMIT=0`, because alpha.28's full proof still waits for host load after
      its readiness gates. Done when every step passes on macOS, including a passing status after
      the candidate step that status names.

## 2. Specification

- [x] 2.1 Write the `distribution` delta. Done when strict validation and the cumulative archive
      simulation pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
  No published prerelease carries an attestation yet, so the local rehearsal of task 1.5 stands in
  for a hosted journey before landing.
- The Change lands before `v0.2.0-alpha.29`, so that release run's `release-journey` legs qualify
  it on macOS and Linux; their passing receipts are the beta journey evidence, and the local
  `release-accept.sh` retires. A failing leg is fixed in a follow-up Change and rerun with a
  `journey_tag` dispatch.
