# Tasks

## 1. Tighten the list

- [x] 1.1 Remove the stray blank line from the 0.2.0-beta.7 entry's Added list. Done when the list
      parses tight, no other line of `CHANGELOG.md` changes, and Prettier's check passes. In
      `6f985fee8`: one blank line left the Added list, the list parses tight, `git diff --stat`
      shows one deletion and nothing else, and Prettier's check passes.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. At `6f985fee8` the static precheck passed and readiness passed 28 of 28 gates.
