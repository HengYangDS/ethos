# Tasks

## 1. One owner of the handoff subject rule

- [x] 1.1 Move the rule into `_package_subject` and call it from import and revoke. Done when the
      decision-density test that refused `revoke_cross_host_source` at 23 passes, and the handoff
      tests pass. RED: proof b28p1 at `bfaaa673a` failed that test (pinned 22, measured 23); GREEN in
      `cfae07bbc`: the density test, the handoff tests and the lease command tests ran 32, all
      passing.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At `cfae07bbc`: `tests/architecture` ran 292 tests, all passing,
      the static precheck passed, and readiness passed 28 of 28 gates.
