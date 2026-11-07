# Tasks

## 1. Retained Repair Scope

- [x] 1.1 Specify with the real repair that the retained fixture's repaired set includes its
      branch-role normalizations. Done when the unit test fails on the current exact-equality check.
      Red at 12:31:34: the real preview on the retained fixture repaired the two retired gaps and
      six branch-role gaps, and the exact check refused with
      `package_retained_publication_repair_failed`, as release run 42331951579 did.
- [x] 1.2 Require the retired gaps, admit only branch-role gaps beside them, and record the list.
      Done when that test and the delivery runtime tests pass. Green at 12:36:23. At 12:35:28 the
      191 delivery tests pass.
