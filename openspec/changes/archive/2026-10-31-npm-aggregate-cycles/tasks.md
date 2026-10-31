# Tasks

## 1. Cyclic Aggregates

- [x] 1.1 Add a regression in which a peer cycle reaches the approved advisory and see it fail with
      `finding_identity_unavailable`. Done when the focused dependency-audit tests show that failure
      before the change. (On `f3519cdf2` the cycle case decided `unknown` where the acyclic report
      decides `block`.)
- [x] 1.2 Resolve aggregates by reachability. Done when the regression passes, an advisory-free
      cycle still reports `finding_identity_unavailable`, and the dependency-audit tests pass. (The
      129 dependency-audit tests passed. The captured `3cdfaebb2` release audit, unknown before, now
      blocks on the minimatch, glob and follow-redirects findings that it names.)

## Workflow follow-up

- Archive this Change with `supply-currency` in the same lane and prove the lane head once.
