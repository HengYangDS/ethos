# Tasks

## 1. Feed every part of `forgeRepository`

- [ ] 1.1 Parse `forgeRepository` values as remote URLs. Done when the feed test with a
      `forgeRepository` on a web port fails before the change and passes after, its port joins the
      feed and its path is the namespace path alone.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests with `tests/architecture`, the precheck and readiness at the lane
      head. Done when each passes on the committed head.
