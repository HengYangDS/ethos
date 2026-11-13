# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.10. Done when the lane's `ethos --version` reports
      0.2.0-beta.10 and the tests that read the version or the changelog pass. Evidence: the lane
      reports `ethos 0.2.0-beta.10`, and on the tree that `28a7a3e98` commits the 37 test files that
      read `VERSION`, the CHANGELOG or a 0.2.0 beta version, with `tests/architecture`, passed 1,044
      tests with 1 skipped by design at 14:33:57.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.10` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.10 as
      its release target and the entry names every advisory that the audit reports. Evidence:
      `changelog_errors` reported nothing with 0.2.0-beta.10 as the release target at 14:18:04. The
      entry carries beta.9's known open defects, still open: the release audit at `82fc6a8b0` passed
      at 14:12:06 with no unapproved finding and reported only npm 12.2.2's bundled glob 13.0.6 and
      minimatch 10.2.5 as unfixed upstream, and CUE, Vale and shfmt have no release built with a
      fixed Go; the release audit is read again before the tag.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: at `66f54c24a` the static precheck from `82fc6a8b0` passed with no finding at
      14:38:39, and readiness passed 28 gates with none failing at 14:38:35. The tests that read the
      version or the changelog passed 1,044 with 1 skipped by design (task 1.1).
