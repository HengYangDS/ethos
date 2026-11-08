# Tasks

## 1. Verifier

- [x] 1.1 Count only hexadecimal runs as malformed markers. Done when a test shows truncated and
      uppercase labels refusing and a placeholder, the bare suffix and a code span admitted, and a
      commit adding the documentation form under a record root yields no marker gap. Evidence:
      `test_only_a_run_of_hexadecimal_labels_can_be_a_malformed_marker` and the `described` case of
      `test_a_marker_edit_pairs_with_what_it_replaced` failed 4 cases with 19 passing before the fix
      (06:05:55 to 06:06:02, uncommitted on 45528d1e8) and passed 23 after it (06:06:15 to
      06:06:18); at 20980ad92 they pass in the impacted sweep (312 files: 5,719 passed and 2
      skipped, 06:11:32 to 06:35:47), and over the 25 revisions of `142092d35..20980ad92` the
      verifier finds no gap while the former regex finds exactly the two CI gaps (06:23:57 to
      06:23:58).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: at 20980ad92 the static precheck passed with no finding over 56 changed files
      (06:22:58 to 06:23:01), readiness passed 28 gates (06:13:22 to 06:14:48), the impacted sweep
      passed (312 files: 5,719 passed and 2 skipped, 06:11:32 to 06:35:47) and the host gate
      `local-install-smoke` passed (06:36:08 to 06:46:38).
