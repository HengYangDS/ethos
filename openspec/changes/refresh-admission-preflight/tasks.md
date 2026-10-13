# Tasks

## 1. Refresh admission

- [x] 1.1 Check the hook runtime binding before a rebase refresh that changes the lane; done when an unarmed binding blocks with its gaps and next action and no rebase runs.
- [x] 1.2 Carry native process failure evidence on refused refresh effects; done when a refused ref transaction reports `process_failure` with its stderr.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation, Ruff, ty and the refresh and lane lifecycle tests; done when all pass with no unrelated tracked change.
