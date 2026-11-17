# Tasks

## 1. Removal and step

- [ ] 1.1 Remove the two unused helpers from the support module of the command runner and from
      the tests of the hosted tool supply. Done when the budget tool reads -12.9 for the tests
      against the lane base, Ruff accepts both modules and the tests of the hosted tool supply
      pass.
- [ ] 1.2 Record the necessity review in DR-0031, index it, and set the test ceiling to 115,000 in
      `.config/checks/format-selection/policy.toml`. Done when the decision registry reports no gap
      for DR-0031 and Prettier and Vale accept the record, the index and this Change's documents.

## 2. Lane only

- [ ] 2.1 Measure the three ceilings at the lane head. Done when the reading states the test
      line-equivalents and DR-0031's figures match it or are corrected to it.
- [ ] 2.2 Pass the source-budget gate with the new ceiling. Done when the lane's report passes with
      no gap.
- [ ] 2.3 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
