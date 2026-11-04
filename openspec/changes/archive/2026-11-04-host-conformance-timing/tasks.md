# Tasks

## 1. Projection

- [x] 1.1 Upload the execution events with each host conformance receipt. Done when the GitHub and
      GitLab host conformance jobs in `.config/ci/pipeline.cue` upload `smoke.events.jsonl` with
      `smoke.json`, and the new architecture test failed before the change.
- [x] 1.2 Regenerate the projections. Done when `ethos lane project --check` reports `conforming`.
- [x] 1.3 Record the change in the changelog. Done when the Unreleased section of `CHANGELOG.md`
      names it under Changed.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
- After landing, the span profile of the first `windows-11-arm` upload goes to the owner's decision
  on that leg.
