## 1. Current-baseline replay

- [x] 1.1 Re-observe the named ownerless source lane and record that accepted
  truth lacks its tracked-invalid-scope recovery behavior.
- [x] 1.2 Add the focused regression for exact repair, unselected, and widened
  scope requests.
- [x] 1.3 Implement the narrowly bound recovery in the shared scope reader.

## 2. Evidence and lifecycle

- [x] 2.1 Add a dated Chronicle and claim binding source head, current replay,
  focused regression, and deferred retirement boundary.
- [x] 2.2 Run focused tests, lifecycle validation, claims/schemas, parity, and
  current-lane plan/proof readiness (executed exact-HEAD proof remains post-commit).
- [x] 2.3 Prepare the current replay, evidence, and OpenSpec carrier for the
  bounded local commit-and-archive transition.
- [x] 2.4 Commit and archive the current replay; post-archive proof, land,
  accepted closeout, and source re-observation remain governed transitions.

## Post-Archive Transition Boundary

Official archive does not itself execute HEAD-bound proof, candidate land,
accepted-root closeout, source-lane retirement, remote publication, or hosted
CI. Each requires current local command evidence; the historical source remains
untouched until accepted closeout and fresh re-observation.
