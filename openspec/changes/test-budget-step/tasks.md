# Tasks

## 1. Step

- [x] 1.1 Record the necessity review in DR-0023, index it, and set the test ceiling to 105,000 in
      `.config/checks/format-selection/policy.toml`. Done when the lane's source-budget gate passes
      and reports the test line-equivalents at the lane head. In `e59dcb159`: DR-0023 records the
      review and is indexed, and the test ceiling reads 105,000. The lane source budget passes with
      no gap: tests 99,899 of 105,000, product 77,728 of 80,000, tools 8,378 of 10,000.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. At `e59dcb159` the static precheck passed and readiness passed 28 of 28 gates.
