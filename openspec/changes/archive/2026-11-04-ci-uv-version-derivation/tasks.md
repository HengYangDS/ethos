# Tasks

## 1. Projection

- [x] 1.1 Derive the uv setup version from the Mise configuration. Done when the CI model names no
      uv version, and the new architecture test that compiles the projections with another Mise uv
      version failed before the change.
- [x] 1.2 Rename the projection input to `mise`. Done when `ethos lane project --check` reports
      `conforming` with unchanged projections.
- [x] 1.3 Record the change in the changelog. Done when the Unreleased section of `CHANGELOG.md`
      names it under Changed.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass.

## Workflow follow-up

- Before the proposal is published, the supply image is rebuilt and bound for this lane's inputs.
- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
