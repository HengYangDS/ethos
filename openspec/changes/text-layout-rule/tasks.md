# Tasks

## 1. Canonical text

- [x] 1.1 Add `canonical_text` with tests, and apply it in `lane format`, the source-format gate and
      `pre-commit`. Done when a hygiene file with a doubled or edge blank line fails the check
      before the change, passes after `lane format --apply`, a second fix changes nothing, and a
      staged violation refuses with its path and line. Evidence: d0cfdfb27 adds
      `repository/paradigm/text_layout.py` (9 unit tests) and applies it in `lane format`, the
      source-format gate and `pre-commit`. Before the wiring the gate passed a `.gitignore` with
      edge and doubled blank lines and a `VERSION` with no final newline, and `pre-commit` admitted
      both staged violations (23:09:46 to 23:09:56); after it the gate refuses both,
      `lane format --apply` repairs them, the check then passes, and `pre-commit` refuses
      `pre_commit_text_layout:<path>:<line>` (5 passed, 23:14:32 to 23:14:56).
- [x] 1.2 Point the policy rows at `ethos lane format`, add the CI supply files, write the reference
      table and the `CHANGELOG.md` line. Done when the format-selection tests pass and Prettier and
      Vale accept the documents. Evidence: d0cfdfb27 points the four canonical-text rows at
      `ethos lane format` and adds the CI supply files, adds the configuration reference's
      per-format table and the Breaking line; the format-selection tests passed (28, after the
      vocabulary test names the product check), and Prettier and Vale accepted the documents in the
      commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 9ebeae1c8 with 0 findings (23:45:28 to 23:45:48),
      and readiness passed 28 gates at 9ebeae1c8 with the 6 heavy gates left to the proof (23:45:48
      to 23:47:58).
