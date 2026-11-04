# Tasks

## 1. Preview and hook agreement

- [x] 1.1 Block an absorbed-ref preview that the prepared hook would refuse. Done when tests show
      that a protected legacy role ref blocks with `legacy_role_ref_protected` and a closeout next
      action, that a deletion with no governing policy blocks with `ref_move_policy_unavailable`,
      that neither emits an apply command, and that each test failed before the change. Both
      previews passed before the change, with `pass` and no gaps.
- [x] 1.2 Admit deleting a legacy role ref that duplicates its successor. Done when a test shows
      that the absorbed-ref retirement deletes such a ref under the installed hook while its
      successor and the other refs stay unchanged, that a legacy ref at another commit stays
      protected, and that the test failed before the change. The hook refused the duplicate with
      `legacy_role_ref_protected`, and the other case reached the CAS as `git_effect_cas_rejected`.
      The 4 new tests and the 515 tests of the retirement, rename, admission and hook suites pass.

## 2. Specification

- [x] 2.1 Write the `repository-governance` and `repository-paradigm` deltas. Done when strict
      validation and the cumulative archive simulation pass. Both pass; after the lane's
      `host-admission` and this Change, all 12 specifications are valid.
