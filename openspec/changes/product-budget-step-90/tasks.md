# Tasks

## 1. Removal and step

- [x] 1.1 Remove the unused constant from `src/ethos/contracts/semantic.py`, record the decision
      and its review in DR-0036 in the form, mark the two sentences of DR-0025 that it replaces,
      index it, and set the product ceiling to 90,000 in
      `.config/checks/format-selection/policy.toml`. Done when the decision registry reports no gap
      and Prettier and Vale accept the records, the index and this Change's documents.
      (At `9d9303b63`: the constant `_COMMITMENT_DIGEST_INVALID` removed, DR-0036 with
      `updates: DR-0025`, two marks in DR-0025, its row in the index and the ceiling at 90,000. The
      docs registry reports no gap; the commit's Markdown width, spacing, Prettier and Vale checks
      and the strict OpenSpec validation pass.)

## 2. Lane only

- [x] 2.1 Measure the three ceilings at the lane head. Done when the reading states the product
      line-equivalents and DR-0036's figures match it or are corrected to it.
      (Read on 2026-11-24 at accepted `dev` `3c6260017` and at the lane head `9d9303b63`: product
      84,888 at both, its code tokens 600,520 before the removal and 600,517 after it; tests
      114,272; tools 8,910. DR-0036 states 84,888 and 114,272.)
- [x] 2.2 Pass the source-budget gate with the new ceiling. Done when the lane's report passes with
      no gap.
      (At `9d9303b63` the source-budget report passes with no gap at 84,888 of 90,000.)
- [ ] 2.3 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
