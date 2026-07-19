## 1. Carrier And RED Baseline

- [x] 1.1 Create the official active Change and bind its claim, dated Chronicle,
  and exact material scope.
- [x] 1.2 Add a zero-foreign-lane regression proving full mode is exact and the
  current bounded mode incorrectly returns `exact` instead of `deferred`.
- [x] 1.3 Validate the carrier, lifecycle, claim, and config surfaces, then
  commit the RED baseline without production changes.

## 2. Explicit Reader Mode Repair

- [x] 2.1 Add the explicit `defer_details` aggregation input without inferring
  mode from foreign-lane contents.
- [x] 2.2 Pass the bounded/full selection from `workspace_status` and preserve
  all five aggregate semantics.
- [x] 2.3 Run the focused lane-status regressions and schema validation green.
- [x] 2.4 Reproduce the concurrently landed exact-empty test failure against the
  corrected implementation.
- [x] 2.5 Restore the preceding status/orient assertions and supersede the
  conflicting active claim and future-dated Chronicle.
- [x] 2.6 Re-run combined lane-status and product projection regressions green.

## 3. Governed Local Closeout

- [ ] 3.1 Run applicable lint, broader tests, claim/lifecycle checks, and generic
  parity on stable committed heads.
- [ ] 3.2 Execute required HEAD-bound default/full proof and verify official
  archiveability.

Candidate landing, accepted-root closeout, remote publication, exact-SHA hosted
CI, and Work Lane retirement remain separate post-archive transitions.
