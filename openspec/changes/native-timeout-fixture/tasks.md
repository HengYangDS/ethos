# Tasks

## 1. A load-independent timeout fixture

- [ ] 1.1 Move the timeout variant's sentinel ahead of pytest and Ruff. Done when, with the budget
      cut below the old critical path, the old fixture fails on the missing sentinel and the new one
      passes, and the committed fixture passes the Nox test module with its 15-second budget.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
