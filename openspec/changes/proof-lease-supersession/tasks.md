# Tasks

## 1. Supersede earlier Lease generations

- [ ] 1.1 Drop a lane's proofs of a lower recorded Lease generation before the binding and
      contradiction comparisons. Done when a HEAD proved under generations 1 and 2 by different
      verifiers selects the generation 2 proof in a repository transition, two proofs of one
      generation with different verifiers still report `contradiction`, and the test fails before
      the change.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests, the precheck and readiness at the lane head. Done when each
      passes on the committed head.
