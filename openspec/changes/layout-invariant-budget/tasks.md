# Tasks

## 1. Measure and policy

- [x] 1.1 Add the layout-invariant code-token count to `ethos.measure`. Done when its tests show
      that a wrapped call with a trailing comma and its one-line form count the same, and that
      comments, docstrings and statement semicolons count nothing. At 17:11:51 the 158 measure,
      budget and retention tests passed, among them the three wrapped-and-joined cases and the
      code-only cases of `layout_invariant_code_tokens`.
- [x] 1.2 Enforce a Python category with a declared tokens-per-line ratio in line-equivalents, and
      keep the line measure for the cross-check and the per-file ceiling. Done when the
      source-budget tests show that a reformatted file leaves `enforced_metrics` unchanged, that a
      category without a ratio is still enforced on lines, and that a malformed ratio fails closed.
      At 17:11:51 `test_a_reformat_leaves_the_enforced_python_coordinate_unchanged` passed (4 and 1
      lines, 8 tokens, 4 line-equivalents for both forms), as did the three malformed-ratio cases;
      the existing boundary test still enforces lines without a ratio.
- [x] 1.3 Declare the ratios, the test ceiling of 100,000 and the tools ceiling of 10,000 in
      `.config/checks/format-selection/policy.toml`. Done when the lane's source-budget gate passes
      and reports the product, test and tools line-equivalents. At 17:14:18 the lane source budget
      passed with no gap: product 73,163 of 75,000, tests 95,657 of 100,000 and tools 8,300 of
      10,000 line-equivalents, from 517,571, 697,726 and 59,218 code tokens.

## 2. Record

- [x] 2.1 Write DR-0019 with the conversion, the necessity review for the test step, the tools
      ceiling, the correction of DR-0010's 512-line figure and the rejection of
      `product-budget-densify`, and index it. Done when the documentation gates pass. DR-0019 is
      written and indexed in `docs/decisions/README.md`; Prettier and Vale passed on every Markdown
      file of the Change at the 17:13 commit `6761303dc`.
