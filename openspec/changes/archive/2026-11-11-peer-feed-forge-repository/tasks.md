# Tasks

## 1. Feed every part of `forgeRepository`

- [x] 1.1 Parse `forgeRepository` values as remote URLs. Done when the feed test with a
      `forgeRepository` on a web port fails before the change and passes after, its port joins the
      feed and its path is the namespace path alone. RED: the feed test with a `forgeRepository` on
      port 8929 failed with the feed ports missing 8929; GREEN: the feed module's 8 tests pass, the
      port joins the feed and the path is the namespace path alone. The decision-density pin of
      `feed_from_config` follows its measured 25 (27 before).

## 2. Acceptance

- [x] 2.1 Pass the impacted tests with `tests/architecture`, the precheck and readiness at the lane
      head. Done when each passes on the committed head. At `0a8a93702`: the 40 impacted test
      targets with `tests/architecture` ran 340 tests, all passing, the static precheck passed with
      no finding, and readiness passed 28 of 28 gates.
