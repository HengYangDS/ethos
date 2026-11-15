# Tasks

## 1. Removal and step

- [x] 1.1 Remove the duplicated scaffolds and the two repeated cases from the four test modules.
      Done when the budget tool reads -51.1 for the tests against the lane base and the four
      modules' tests pass. The budget tool reads -51.1 against `5a5b51f51`, and the four modules' 60
      tests pass (hosted runs of `fcd3e45c2` on both forges).
- [x] 1.2 Record the necessity review in DR-0028, index it, and set the test ceiling to 110,000 in
      `.config/checks/format-selection/policy.toml`. Done when the decision registry reports no gap
      for DR-0028 and Prettier and Vale accept the record, the index and this Change's documents.
      The documentation registry reports no gap at `8011d3707`; Prettier and Vale accept the five
      documents.

## 2. Lane only

- [x] 2.1 Measure the three ceilings at the lane head. Done when the reading states the test
      line-equivalents and DR-0028's figures match it or are corrected to it. The source-budget
      gate's report at `8011d3707`: tests 104,704 with 5,296 free of 110,000; product 81,263; tools
      8,622. The record was corrected to it in `8011d3707`.
- [x] 2.2 Pass the source-budget gate with the new ceiling. Done when the lane's report passes with
      no gap. The gate's report passes with no gap at `8011d3707`, in readiness and in the hosted
      runs of `fcd3e45c2`.
- [x] 2.3 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The static pre-check and readiness passed at `8011d3707`, and the hosted runs of
      `fcd3e45c2` passed on both forges; the three commits after it change documents only.
