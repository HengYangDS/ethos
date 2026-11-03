# Tasks

## 1. Proof execution

- [x] 1.1 Run a full proof that plans only readiness gates without entering admission. Done when a
      proof execution test shows that such a plan runs its gates with no admission and that a plan
      with a test gate still waits once after readiness, and the new case failed before the change.
- [x] 1.2 Record the change in the changelog. Done when the unreleased readiness-gate entry under
      Changed in `CHANGELOG.md` names it.

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
