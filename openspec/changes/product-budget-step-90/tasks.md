# Tasks

## 1. Removal and step

- [x] 1.1 Remove the unused constant from `src/ethos/contracts/semantic.py`, record the decision
      and its review in DR-0036 in the form, mark the two sentences of DR-0025 that it replaces,
      index it, and set the product ceiling to 90,000 in
      `.config/checks/format-selection/policy.toml`. Done when the decision registry reports no gap
      and Prettier and Vale accept the records, the index and this Change's documents.
      (Commit `cc6eeacd4`: the constant `_COMMITMENT_DIGEST_INVALID` removed, DR-0036 with
      `updates: DR-0025`, two marks in DR-0025, its row in the index and the ceiling at 90,000. The
      docs registry reports no gap, and the Markdown, Prettier, Vale and strict OpenSpec checks pass
      in the full pre-check at `70613bc6f`.)

## 2. Lane only

- [x] 2.1 Measure the three ceilings at the lane head. Done when the reading states the product
      line-equivalents and DR-0036's figures match it or are corrected to it.
      (Read on 2026-11-26 by the source-budget report: accepted `dev` `cdb51d469` reads product
      84,888, the figure DR-0036 states; the lane head `70613bc6f` reads product 84,980, tests
      114,708 and tools 8,910.)
- [x] 2.2 Pass the source-budget gate with the new ceiling. Done when the lane's report passes with
      no gap.
      (At `70613bc6f` the source-budget report passes with no gap at 84,980 of 90,000.)
- [x] 2.3 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. (Both pass at `70613bc6f`.)
