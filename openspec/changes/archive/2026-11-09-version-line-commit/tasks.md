# Tasks

## 1. Version line

- [x] 1.1 Print the source commit in the human version line. Done when a version test that compares
      the line's commit field with the JSON projection's `source_commit` fails before the change and
      passes after it. Evidence: `test_version_human_output_is_concise`, which now compares the
      line's commit field with the JSON projection's `source_commit`, failed before the change, the
      line reading `; ; OpenSpec 1.16.0)` (09:36:07 to 09:36:11, uncommitted on c9aff59da), and
      passes after it (5 passed, 09:36:26 to 09:36:37); the impacted sweep at a7bbbef8d passed (359
      files: 6,988 passed and 2 skipped, 09:50:47 to 10:30:24).

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. Evidence: at a7bbbef8d the static precheck passed with no finding over 41
      changed files (09:51:36 to 09:51:42), readiness passed 28 gates (09:49:09 to 09:50:00) and the
      impacted sweep at a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to
      10:30:24).
