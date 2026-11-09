# Tasks

## 1. Behaviour

- [x] 1.1 Report and delete an unread release key. Done when paradigm tests show `version_source`
      and `tag_pattern` reported as `release-binding`, also without release tags, and deleted by the
      repair in the same pass that keeps `mirror`; a `[release]` left empty removed with its
      comments; and a multi-line value beside the mirror left reported. `_RELEASE` in
      `test_paradigm_repair.py` and the release fixture of
      `tests/unit/cli/test_lane_paradigm_repair.py` drop the two keys; the accepted-mirror
      `release-table` case keeps them and asserts that the same pass deletes them. In the impacted
      sweep of 336 test files at `a76cb7db7` (19:38:11 to 20:37:47, 6,571 passed, 2 skipped),
      `test_an_unread_release_key_is_deleted` (three cases),
      `test_an_unread_release_key_on_several_lines_beside_the_mirror_stays_reported` and
      `test_an_accepted_mirror_moves_to_the_release_binding` (three cases) passed.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The batch precheck passed with 0 findings at 20:51:27 to 20:51:49 against
      `0f788d4a6`, and readiness passed 28 gates from 20:46:13 to 20:51:07, both at `a12fcb313`. The
      impacted sweep of 336 test files at `a76cb7db7` passed 6,571 tests and failed 3 from 19:38:11
      to 20:37:47; `a12fcb313` fixed those 3, whose 2 files passed 16 tests from 20:45:41 to
      20:46:02, and the 34-file impacted sweep of the change since `a76cb7db7` passed 281 tests from
      20:43:26 to 20:45:09, both at `a12fcb313`.
