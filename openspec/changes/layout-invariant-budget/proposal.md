# Proposal

## Why

The source budget counts token-bearing physical lines (`src/ethos/measure.py:44-63`), so a
formatter pass that changes no code moves it. In this period three Changes freed budget by layout
alone: `test-budget-margin` and `test-budget-densify-2` (landed) and `product-budget-densify`
(proven, never landed). Measured on the same trees, their code tokens did not move: the product
stayed at 517,133 tokens while its lines fell from 73,100 to 70,868, and the tests stayed at 691,974
tokens while their lines fell by 175 in `214133da5`. The PDC calls such repairs invalid
("relabeling, cosmetic compression, removed necessary tests or automatic limit increases are
invalid repairs", PDC line 487), the quality specification says formatting compression cannot
remediate a budget gap, and DR-0010 rejected raw LOC because formatting can game it. The 2026-11-07
expert committee therefore made a layout-invariant measure the first RC-blocking Change (resolution
R3, `build/runtime/work/committee-20261107/resolution-r3.md`).

## What Changes

- The Python budget categories count layout-invariant code tokens: the tokens that remain after
  comments, line structure, standalone string expressions, statement semicolons and a comma directly
  before a closing bracket are removed. A reformatted file keeps its count.
- The ceilings stay in line-equivalents. The policy declares a tokens-per-line ratio for each Python
  category, taken once from the trees before the formatter-only collapses: product 7.0743 at
  `c3ca98963`, tests 7.2941 at `44c3bd5a1`, tools 7.1347 at `c3ca98963`. An enforced coordinate is
  its token total divided by its ratio, rounded up.
- The physical-line measure stays where it is the right one: the native `scc` cross-check and the
  500-line per-file tripwire that adopters share are unchanged.
- Under the new measure the tests sit at 95,596 line-equivalents, above their 95,000 ceiling, because
  the formatter's savings no longer count. A necessity review in DR-0019 takes the test ceiling one
  5,000 step to 100,000. `tools/` gets its first ceiling, 10,000 line-equivalents, against 8,300 today.
- DR-0019 records the decision, the conversion, the review and the correction of DR-0010's stale
  512-line per-file figure to the enforced 500.
- Rejected: `product-budget-densify`, a formatter-only collapse of 192 product modules (AST-equal),
  withdrawn because it freed budget by layout alone (PDC line 487). Its lane was retired as a
  reviewed abandonment on 11-07; its three commits are kept as a bundle in the lane toolkit until this
  Change lands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the Direct Source Budget requirement names the layout-invariant measure and the
  line-equivalent ceilings.

## Impact

- `src/ethos/measure.py`, `src/ethos/domain/source_budget/measurement.py`,
  `src/ethos/repository/policy/quality/source_budget.py`, `.config/checks/format-selection/policy.toml`
  and their tests.
- `docs/decisions/dr-0019-layout-invariant-source-budget.md` and `docs/decisions/README.md`.
- Adopters: no change. The per-file ceiling and a policy without a tokens-per-line ratio keep the
  line measure.
