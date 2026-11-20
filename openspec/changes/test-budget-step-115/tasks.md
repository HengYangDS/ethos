# Tasks

## 1. Removal and step

- [x] 1.1 Remove the two unused helpers from the support module of the command runner and from
      the tests of the hosted tool supply. Done when the source-budget gate's reading for the
      tests falls by the two helpers' measure, Ruff accepts both modules and the tests of the
      hosted tool supply pass.
      (At `6446956e2` the gate's reading for the tests falls from 109,497 to 109,484; Ruff accepts
      both modules; the hosted tool supply module and two importers of the support module pass, 79
      cases.)
- [x] 1.2 Record the necessity review in DR-0033 in the form, mark the two sentences of DR-0028
      that it replaces, index it, and set the test ceiling to 115,000 in
      `.config/checks/format-selection/policy.toml`. Done when the decision registry reports no gap
      and Prettier and Vale accept the records, the index and this Change's documents.
      (At `6446956e2`: DR-0033 with `updates: DR-0028`, two marks in DR-0028, its row in the index
      and the ceiling at 115,000. The docs registry reports no gap; the Markdown lint and the prose
      gate pass on the six documents with a refusing control.)

## 2. Lane only

- [x] 2.1 Measure the three ceilings at the lane head. Done when the reading states the test
      line-equivalents and DR-0033's figures match it or are corrected to it.
      (Read at the lane head on 2026-11-19: tests 109,497 before the removal and 109,484 after it,
      product 82,985, tools 8,908. DR-0033 states the two test readings.)
- [x] 2.2 Pass the source-budget gate with the new ceiling. Done when the lane's report passes with
      no gap.
      (At `6446956e2` the source-budget report passes with no gap at 109,484 of 115,000.)
- [x] 2.3 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.)
