# Tasks

## 1. Inert test repositories

- [x] 1.1 Declare the Git isolation settings once and apply them to every case and to the CLI
      runner. Done when a fixture commit traced with trace2 starts no `maintenance` process and the
      configuration tests pass. Evidence: at aeeee2220 `tests/support/git_isolation.py` declares
      `GIT_ISOLATION`, which the suite overlay and the CLI runner read.
      `test_a_test_repository_commits_without_background_maintenance` failed before the change with
      one `git maintenance run --auto --detach` start (12:43:29 to 12:43:36) and passed after it
      with the configuration and gate-policy modules (37 passed, 12:44:37 to 12:44:59); the 19 test
      targets that read the Git overlay or run maintenance passed at aeeee2220 (609 passed, 1
      skipped, 12:47:02 to 12:55:58).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against bd0edc28c with 0 findings (13:11:27 to 13:11:31)
      and readiness passed 28 gates at deb761f85 with the 6 heavy gates left to the proof (13:09:08
      to 13:10:26).
