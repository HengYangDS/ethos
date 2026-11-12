# Tasks

## 1. Product budget step

- [x] 1.1 Delete `binds_custody`, write DR-0025 and its index line, and move the product ceiling to
      85,000. Done when the source-budget report passes and the decision registry accepts DR-0025.
      Evidence: f60574afb deletes `binds_custody`, adds DR-0025 and its index line and moves the
      product ceiling to 85,000; the source-budget report then measured 80,126 against 85,000 with
      no gap, after 80,175 at readiness and 80,130 after the merge in 7b562d098.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
