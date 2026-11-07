---
subject: ethos:decision:layout-invariant-source-budget
role: decision
state: canonical
decision_id: DR-0019
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/quality/spec.md
---

# DR-0019: The Source Budget Counts Code, Not Layout

Status: canonical rationale. The quality specification owns current behavior.

Date: 2026-11-07.

Purpose: preserve why the Python source-budget ceilings count layout-invariant code tokens in
line-equivalents, where the conversion came from, and why the test ceiling moved one step.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md), the
[quality specification](../../openspec/specs/quality/spec.md) and the `layout-invariant-budget`
OpenSpec Change.

## Context

DR-0010 rejected raw LOC as semantic currency because formatting can game it, and the quality
specification says formatting compression cannot remediate a budget gap. The implemented measure
nevertheless counted physical lines that hold a token, so a formatter pass that keeps the syntax
tree lowered it. Between 11-06 and 11-07 three Changes freed budget that way. Measured on the same
trees, the product kept 517,133 code tokens while its lines fell from 73,100 to 70,868, and the
tests kept 691,974 tokens while their lines fell by 175 in one of them. The PDC names cosmetic
compression an invalid repair, and the 2026-11-07 expert committee made a layout-invariant measure
its first RC-blocking resolution (R3).

## Decision

- A Python category with a declared tokens-per-line ratio is enforced in line-equivalents: its
  layout-invariant code tokens divided by the ratio, rounded up. The tokens exclude comments, line
  structure, standalone string expressions, statement semicolons and a comma directly before a
  closing bracket.
- The ratios were measured once, on the trees before the formatter-only collapses, so the
  formatter's lines earn nothing: product 7.0743 at `c3ca98963`, tests 7.2941 at `44c3bd5a1`, tools
  7.1347 at `c3ca98963`. A ratio changes only like a ceiling, through a reviewed Change.
- The physical-line measure stays the native cross-check's comparison and the per-file ceiling's
  measure, so adopters see no change. The per-file ceiling is 500 lines; DR-0010's "512-ELOC
  per-file limit" was stale when it was written and this record corrects it.
- Necessity review for one test step under DR-0010 and the owner's 2026-11-01 rule. The tests
  measure 697,284 tokens, 95,596 line-equivalents, against 95,000. This period's real reductions
  were small: `test-budget-densify` removed 486 tokens by moving repeated calls into helpers, and
  `result-contract-budget` removed 123 with redundant plumbing; the formatter-only collapses removed
  none. The remaining space is the acceptance the committee made RC-blocking. The next reduction is
  structural: a Git port with an in-memory adapter to replace patch-based tests (resolution R2,
  0.3.0), not more compression. The test ceiling therefore moves one 5,000 step to 100,000.
- `tools/`, which holds the release harness where release-time failures recur, gets its first
  ceiling: 10,000 line-equivalents, the first 5,000 boundary above its 8,300.
- `product-budget-densify` is rejected: a formatter-only collapse of 192 product modules, proven
  but never landed. Its three commits are kept as a bundle in the lane toolkit until the Change that
  records this decision lands.

## Alternatives Rejected

- **Keep counting lines:** formatting moves it, as the measurements show.
- **Count AST nodes:** fully layout-invariant, but not the measure the committee approved, and node
  shapes differ across supported Python minor versions.
- **Count tokens of `ast.unparse` output:** invariant, but tied to each interpreter's unparser.
- **Ceilings in raw tokens:** loses readable limits and the 5,000-step rule.
- **Ratios from today's trees:** they already contain the formatter collapses, so the conversion
  would credit about 2,000 lines of layout.
- **No test step:** the tests would stay blocked while the RC's own acceptance needs space, and the
  only quick lever left is the compression this record rejects.

## Consequences and Boundary

- A reformatted file keeps its enforced count; its physical lines may still change for the
  cross-check and the per-file ceiling.
- Grouping parentheses still count, and a formatter may add a pair when it rewraps an assignment: 2
  tokens across the 192 collapsed modules.
- Reports carry token totals and line-equivalents beside the line metrics, so the two no longer
  agree for Python categories.
- This record does not admit growth by itself; each later step needs a fresh necessity review.

## Evidence and Revisit

Measurements: `build/runtime/work/size-measure/ratio.py` and the `layout-invariant-budget` design.
Revisit when a re-measure of the reference trees moves a ratio by more than 5 percent, when a
formatter is shown to move the token count materially, or when the tests reach 100,000 before the
0.3.0 reduction lands.
