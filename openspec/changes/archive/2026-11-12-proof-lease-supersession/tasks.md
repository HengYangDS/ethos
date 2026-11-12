# Tasks

## 1. Supersede earlier Lease generations

- [x] 1.1 Drop a lane's proofs of a lower recorded Lease generation before the binding and
      contradiction comparisons. Done when a HEAD proved under generations 1 and 2 by different
      verifiers selects the generation 2 proof in a repository transition, two proofs of one
      generation with different verifiers still report `contradiction`, and the test fails before
      the change. `c15ce2c87` keeps, per Work Lane, only the proofs of its latest recorded Lease
      generation once the floor candidates are found.
      `test_a_later_lease_generation_supersedes_a_lanes_earlier_proof` failed first on generations 1
      and 2 with `(None, ['contradiction'])`; after the change both its cases pass, generations 1
      and 2 selecting the generation 2 proof and two generation 2 proofs still reporting
      `contradiction`.

## 2. Acceptance

- [x] 2.1 Pass the impacted tests, the precheck and readiness at the lane head. Done when each
      passes on the committed head. The impacted sweep of 17 targets passed 524 tests at
      `77a15df64`, the static precheck there reports only its own 100-column heuristic on the
      decision index line, whose entries are one line each, and readiness passed 28 of 28 gates at
      `47b200b9d`.
