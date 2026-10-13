# Tasks

## 1. Restore

- [x] 1.1 Restore refused refreshes by switching the detached worktree to the original head before re-attaching; done when a real-Git refused ref update leaves the lane attached at its original head with a clean tree.
- [x] 1.2 Record the pending refresh before the rebase and remove it once the lane is attached; done when success and every restored failure leave no record.
- [x] 1.3 Restore an interrupted refresh from its record on a detached lane; done when a real-Git interrupted refresh followed by `refresh-base --apply` reports `base_restored` attached at the original head, and a moved branch blocks without moving the worktree.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation, Ruff, ty and the refresh and lane lifecycle tests; done when all pass with no unrelated tracked change.
