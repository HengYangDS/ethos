# Tasks

## 1. Measure and policy

- [ ] 1.1 Add the layout-invariant code-token count to `ethos.measure`. Done when its tests show
      that a wrapped call with a trailing comma and its one-line form count the same, and that
      comments, docstrings and statement semicolons count nothing.
- [ ] 1.2 Enforce a Python category with a declared tokens-per-line ratio in line-equivalents, and
      keep the line measure for the cross-check and the per-file ceiling. Done when the
      source-budget tests show that a reformatted file leaves `enforced_metrics` unchanged, that a
      category without a ratio is still enforced on lines, and that a malformed ratio fails closed.
- [ ] 1.3 Declare the ratios, the test ceiling of 100,000 and the tools ceiling of 10,000 in
      `.config/checks/format-selection/policy.toml`. Done when the lane's source-budget gate passes
      and reports the product, test and tools line-equivalents.

## 2. Record

- [ ] 2.1 Write DR-0019 with the conversion, the necessity review for the test step, the tools
      ceiling, the correction of DR-0010's 512-line figure and the rejection of
      `product-budget-densify`, and index it. Done when the documentation gates pass.
