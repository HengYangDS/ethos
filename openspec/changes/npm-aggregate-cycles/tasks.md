# Tasks

## 1. Cyclic Aggregates

- [ ] 1.1 Add a regression in which a peer cycle reaches the approved advisory and see it fail with
      `finding_identity_unavailable`. Done when the focused dependency-audit tests show that failure
      before the change.
- [ ] 1.2 Resolve aggregates by reachability. Done when the regression passes, an advisory-free
      cycle still reports `finding_identity_unavailable`, and the dependency-audit tests pass.

## Workflow follow-up

- Archive this Change with `supply-currency` in the same lane and prove the lane head once.
