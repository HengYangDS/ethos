# Tasks

## 1. Canonical text

- [ ] 1.1 Add `canonical_text` with tests, and apply it in `lane format`, the source-format gate and
      `pre-commit`. Done when a hygiene file with a doubled or edge blank line fails the check
      before the change, passes after `lane format --apply`, a second fix changes nothing, and a
      staged violation refuses with its path and line.
- [ ] 1.2 Point the policy rows at `ethos lane format`, add the CI supply files, write the reference
      table and the `CHANGELOG.md` line. Done when the format-selection tests pass and Prettier and
      Vale accept the documents.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
