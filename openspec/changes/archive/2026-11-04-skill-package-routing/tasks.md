# Tasks

## 1. Unrouted packages

- [x] 1.1 Report `skill_package_unregistered:<directory>` for a package directory that neither an
      active record nor a retirement routes. Done when a test shows the gap for an unrouted package
      and none for a routed one, and the test failed before the change. Before it, the report named
      only `skill_missing_commands:routed`; the module's 17 tests now pass.
- [x] 1.2 Check the fleet. Done when the report's gaps on every governed repository are compared
      before and after the change, and each repository that gains the gap is named here. None of
      the 33 governed checkouts, ETHOS included, gains a gap; di-effect keeps its one missing
      registry gap, because the check runs only when the registry loads.

## 2. Specification

- [x] 2.1 Write the `assistant-projections` delta. Done when strict validation and the cumulative
      archive simulation pass. Both pass; after the lane's four Changes, all 12 specifications are
      valid.
