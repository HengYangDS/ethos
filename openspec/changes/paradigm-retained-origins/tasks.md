# Tasks

## 1. Behaviour

- [x] 1.1 Exclude verified originals from the authored checks. Done when paradigm tests show a byte-
      and mode-verified original, including one named like a decision record and one in a non-kebab
      directory, with no front-matter, decision-record, authored-name or formatter gap, and an
      altered, mode-mismatched or merely declared original, a malformed taxonomy and an ordinary
      document without front matter keeping theirs; the formatter case uses a fixture whose only
      Markdown file is the original. In the impacted sweep of 336 test files at `a76cb7db7`
      (19:38:11 to 20:37:47, 6,571 passed, 3 failed in other files, 2 skipped), the ten report cases
      of `test_paradigm_retained_origins.py`, the formatter pair among them, passed.
- [x] 1.2 Repair no original. Done when a `repair_paradigm` test with a `<!--`-wrapped verified
      original plans no edit of it, and the same file without verification keeps its planned edit.
      In the impacted sweep of 336 test files at `a76cb7db7` (19:38:11 to 20:37:47, 6,571 passed, 3
      failed in other files, 2 skipped), both cases of
      `test_the_repair_plans_no_edit_of_a_verified_original` passed.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The batch precheck passed with 0 findings at 20:51:27 to 20:51:49 against
      `0f788d4a6`, and readiness passed 28 gates from 20:46:13 to 20:51:07, both at `a12fcb313`. The
      impacted sweep of 336 test files at `a76cb7db7` passed 6,571 tests and failed 3 from 19:38:11
      to 20:37:47; `a12fcb313` fixed those 3, whose 2 files passed 16 tests from 20:45:41 to
      20:46:02, and the 34-file impacted sweep of the change since `a76cb7db7` passed 281 tests from
      20:43:26 to 20:45:09, both at `a12fcb313`.
