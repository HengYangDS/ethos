# Tasks

## 1. Behaviour

- [x] 1.1 Report and repair an unread rules table. Done when paradigm tests show `[formats]` and
      `[gates]` reported as `rules-binding` and deleted by the repair; `[paradigm]`, `[profiles]`,
      `[[rule]]`, `[artifacts]` and a `[quality]` holding `code_size` beside another key left to
      their readers and their own gaps; a bare top-level value reported without a repair; and a
      binding left empty deleted. Evidence: `test_an_unread_rules_table_is_deleted` (only unread
      tables, beside the profiles) and the bare-value case of
      `test_a_rules_key_that_is_read_moves_or_is_bare_is_never_deleted` failed before the change (3
      failed, 45 passed, 09:38:30 to 09:38:33, uncommitted on 554cbd4a8) and pass after it (48
      passed, 09:38:57 to 09:39:00); its record-binding, restated-size and read-tables cases pass
      before and after; the 14 paradigm test files pass (420 passed, 09:40:24 to 09:40:29); the
      impacted sweep at a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to
      10:30:24).

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. Evidence: at a7bbbef8d the static precheck passed with no finding over 41
      changed files (09:51:36 to 09:51:42), readiness passed 28 gates (09:49:09 to 09:50:00) and the
      impacted sweep at a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to
      10:30:24).
